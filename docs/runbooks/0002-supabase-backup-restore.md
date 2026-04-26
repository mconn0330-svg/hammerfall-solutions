# Runbook 0002 — Supabase brain backup and restore

**Status:** Active
**Created:** 2026-04-25
**Last verified:** 2026-04-25 (initial restore drill — see "Drill log" below)
**Owner:** Maxwell McConnell

## Symptom

You've broken the brain. One of:

- Accidental `DROP TABLE`, `TRUNCATE`, or large `DELETE` against production
- A migration that destroyed data and the `DOWN:` block isn't enough (data loss not just schema change)
- Supabase project corruption (extremely rare; PITR usually catches this)
- "I want to inspect what production looked like at noon yesterday" (not a failure, but uses the same tooling)

## Diagnosis

Confirm restore is the right action vs other paths:

```bash
# Is the runtime healthy?
curl -fsS http://localhost:8000/health
# 200 → runtime is up and Supabase is reachable. The damage is data-shaped, not service-shaped.

# Is data missing or corrupted?
# Quick row-count sanity (replace with the table you suspect):
curl -fsS -H "apikey: $SUPABASE_BRAIN_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_BRAIN_SERVICE_KEY" \
  "$SUPABASE_BRAIN_URL/rest/v1/helm_memory?select=count" \
  -H "Prefer: count=exact"
```

If the row count is unexpectedly low/zero, restore is the path. If the data is _there_ but _wrong_ (corrupted JSON, bad embedding shapes), restore from before-the-corruption is also the path — but be precise about which backup.

## Fix

### Two backup sources to choose from

1. **Supabase Pro PITR (point-in-time recovery)** — automatic, daily, retained 7 days on Pro tier. Use the dashboard: project → Database → Backups → Restore from a point in time. **This is the primary safety net for "oops, I broke prod."**
2. **Manual `scripts/backup.sh` dumps** in `~/helm-backups/` — belt-and-suspenders. Use these when:
   - PITR doesn't go far enough back (>7 days ago)
   - You want an offline copy (laptop dead-drop, separate drive)
   - You're moving to a new Supabase project entirely

### Restore procedure (staging-first, never direct-to-prod)

**Path A — Supabase PITR (preferred for "undo the last hour"):**

1. Project dashboard → Database → Backups → "Restore" → pick the timestamp.
2. Supabase creates a new project at that point in time. Original is left untouched until you promote.
3. Sanity-check the restored project (row counts, recent rows).
4. Promote: in dashboard, swap the project endpoints — _or_ update `SUPABASE_BRAIN_URL` env var to the restored project's URL and restart the runtime.

**Path B — Manual dump restore (preferred for "weeks ago" or "to a fresh project"):**

1. **Pick the dump.** From `~/helm-backups/`, choose the most recent acceptable timestamp. Files are named `helm-brain-YYYYMMDD-HHMMSS.sql`.

2. **Spin up a Postgres with pgvector** (NOT stock postgres — see "Drill log" below for why):

   ```bash
   docker run -d --name helm-restore \
     -e POSTGRES_PASSWORD=restore \
     -e POSTGRES_DB=helm_brain \
     -p 5499:5432 \
     pgvector/pgvector:pg17
   until docker exec helm-restore pg_isready -U postgres -d helm_brain | grep -q "accepting"; do sleep 1; done
   ```

3. **Pre-create the `extensions` schema with pgvector** (matches Supabase's layout — without this, `CREATE TABLE` fails because the dump references `"extensions"."vector"`):

   ```bash
   docker exec -i helm-restore psql -U postgres -d helm_brain -c "
     CREATE EXTENSION IF NOT EXISTS vector;
     CREATE SCHEMA IF NOT EXISTS extensions;
     ALTER EXTENSION vector SET SCHEMA extensions;
   "
   ```

4. **Apply the dump.** Many GRANT statements will fail with `role "anon" does not exist` — that's expected and harmless. The data restores cleanly. Filter to see only DDL/data outcomes:

   ```bash
   docker exec -i helm-restore psql -U postgres -d helm_brain --quiet \
     < ~/helm-backups/helm-brain-YYYYMMDD-HHMMSS.sql 2>&1 \
     | grep -vE "^ERROR:  role"
   ```

5. **Verify counts.** Compare to what you expected; the dump's `INSERT INTO ... VALUES (...)` blocks have one row per `^\t(...)` continuation line:

   ```bash
   docker exec -i helm-restore psql -U postgres -d helm_brain -c "
     SELECT 'helm_beliefs' AS tbl, COUNT(*) FROM helm_beliefs
     UNION ALL SELECT 'helm_entities',             COUNT(*) FROM helm_entities
     UNION ALL SELECT 'helm_entity_relationships', COUNT(*) FROM helm_entity_relationships
     UNION ALL SELECT 'helm_frames',               COUNT(*) FROM helm_frames
     UNION ALL SELECT 'helm_memory',               COUNT(*) FROM helm_memory
     UNION ALL SELECT 'helm_memory_index',         COUNT(*) FROM helm_memory_index
     UNION ALL SELECT 'helm_personality',          COUNT(*) FROM helm_personality;
   "
   ```

6. **Promote** (only after verification): if the restored data is correct, push it to a fresh Supabase project (`pg_dump` from local → load into new Supabase) OR migrate the runtime to point at the restored Postgres. Never `DROP DATABASE` on prod and re-INSERT — that races against any reads in flight.

7. **Tear down the restore container** when done: `docker rm -f helm-restore`.

**Verification:** the row counts in step 5 match the rows you expected. `/health` against the runtime pointing at the restored data returns 200.

**Irreversible:** None during the restore itself (everything happens in a sidecar Postgres). The promotion step in 6 IS irreversible if you swap the prod endpoint and existing pollers redirect — but as long as the original prod project is untouched (Path B never modifies prod), you can roll back by re-pointing at the original.

## Backup procedure

`scripts/backup.sh` produces a full dump (schema + data) of the `public` schema:

```bash
bash scripts/backup.sh
# Writes to ~/helm-backups/helm-brain-YYYYMMDD-HHMMSS.sql
# Retention: keeps the last 30 dumps; older ones are deleted automatically
```

Schedule daily via cron (T1 acceptable as manual cron; T4.1 / Stage 2 considers automation):

```cron
0 3 * * *  /full/path/to/scripts/backup.sh >> ~/helm-backups/backup.log 2>&1
```

Override paths via env vars: `HELM_BACKUP_DIR` (default `~/helm-backups`), `HELM_BACKUP_RETENTION` (default 30).

## What's NOT backed up

- **Auth users** — none at T1 (Maxwell-only via static bearer token from T0.A8). When user auth lands at Stage 2, this list updates.
- **Storage buckets** — none at T1.
- **Postgres roles** (`anon`, `authenticated`, `service_role`) — Supabase-managed; reprovisioned automatically on restore to a Supabase project. On a non-Supabase target (the docker drill), these GRANTs fail harmlessly.
- **RLS policies** — included in the dump as DDL, restore correctly.
- **Migrations history table** (`supabase_migrations.schema_migrations`) — `supabase db dump --schema public` doesn't include it. This is fine for restore-to-fresh-project (run `supabase db push` after to re-apply migrations cleanly); not fine for "this dump IS the new prod" (you'd lose migration tracking).

## Drill log

**2026-04-25** — Initial drill, run as part of T0.A10:

- Took backup via `bash scripts/backup.sh` against the live `hammerfall-brain` project. Output: `~/helm-backups/helm-brain-20260425-221510.sql` (4.1 MB, 1329 lines).
- Spun up `pgvector/pgvector:pg17` in docker (stock postgres failed — pgvector type required).
- Pre-created `extensions` schema with pgvector inside it (matches Supabase layout).
- Restored the dump. ~20 `ERROR: role "anon"/"authenticated"/"service_role" does not exist` messages from GRANT statements — expected, harmless.
- Verified row counts: 76 / 64 / 349 / 0 / 66 / 7 / 6 across the seven public tables. **All match the source.**
- Tore down the container.

**Friction surfaced (now documented above):**

1. Stock `postgres:17` doesn't have pgvector — `pgvector/pgvector:pg17` is the right base.
2. Dump references `"extensions"."vector"` — the `extensions` schema must exist before applying the dump, with pgvector inside it.
3. Supabase RBAC roles aren't created on a generic Postgres — GRANTs fail. Filter the output to suppress the noise (`grep -vE "^ERROR:  role"`).

Total drill time: ~10 minutes including pulling the docker image.

## Root cause

There is no automated backup automation at T1 by design. The threat model is "single-developer working from one laptop with Supabase Pro PITR as the primary safety net." Manual dumps are belt-and-suspenders, and a documented restore path is the contract that the dumps are _useful_, not just _present_.

- Related code: `scripts/backup.sh`, `scripts/migrate.sh` (`baseline-dump` produces a schema-only variant)
- Related ADRs: ADR 0002 (Migration Reversibility Policy) — for schema-shaped damage that's reversible without restore
- Related findings: none

## Prevention

Reduce restore frequency by:

- **PITR is the first line.** Pro tier gives 7-day point-in-time recovery automatically. For most "oops" incidents, PITR is faster and surgically precise.
- **Reversibility-classed migrations.** ADR 0002 ensures destructive migrations declare a rollback path before they ship — most data loss caused by migrations is therefore avoidable via the documented `DOWN:` block.
- **Don't run destructive SQL against the linked production project.** Always run on a Supabase branch (Pro tier) or a docker postgres first, verify, then push.
- **Cron the backup.** A backup that hasn't been taken can't be restored. Set up the cron entry above; check `~/helm-backups/backup.log` weekly.

What would automate this further (Stage 2):

- Move `scripts/backup.sh` to a scheduled GitHub Actions workflow that uploads dumps to an off-site bucket. Removes the "my laptop is the only place backups exist" risk.
- Add a periodic restore drill (monthly) that runs against a throwaway docker postgres in CI. Detects backup-file regressions before an incident.

---

_Maintenance: Re-verify this runbook after any change to the schema (new tables = new row-count check), any change to `scripts/backup.sh`, or any change to the Supabase project tier (PITR retention). Update "Last verified" date when re-tested._
