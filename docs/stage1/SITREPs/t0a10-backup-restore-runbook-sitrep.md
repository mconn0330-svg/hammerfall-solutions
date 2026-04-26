# SITREP — T0.A10 Backup + Restore Runbook

**Date:** 2026-04-25
**Branch:** `feature/t0a10-backup-restore-runbook`
**Tier:** STOP (spec STOP gate: "Maxwell confirms the restore drill works")
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A10 (lines 716–729)

## Scope executed

Three artifacts plus an actually-executed restore drill:

1. **`scripts/backup.sh`** — cron-friendly. `supabase db dump` (data + schema) → `~/helm-backups/helm-brain-YYYYMMDD-HHMMSS.sql`. Rotation to 30 dumps. Override paths via `HELM_BACKUP_DIR` / `HELM_BACKUP_RETENTION` env vars.

2. **`docs/runbooks/0002-supabase-backup-restore.md`** — the runbook. Covers Symptom → Diagnosis → Fix (two paths: Supabase PITR primary, manual dump restore secondary) → Backup procedure (cron entry included) → What's NOT backed up → Drill log → Root cause → Prevention.

3. **Real restore drill executed end-to-end.** Drill log captured in the runbook. Three friction points documented (now part of the standard procedure).

## Drill results (the spec's STOP-gate condition)

Took a real backup of the live `hammerfall-brain` project, restored it into a sidecar `pgvector/pgvector:pg17` docker container, verified row counts match. **All 7 tables match exactly:**

| Table                       | Source rows | Restored rows                       |
| --------------------------- | ----------- | ----------------------------------- |
| `helm_beliefs`              | 76          | 76                                  |
| `helm_entities`             | 64          | 64                                  |
| `helm_entity_relationships` | 349         | 349                                 |
| `helm_frames`               | 0           | 0 (transient store, expected empty) |
| `helm_memory`               | 66          | 66                                  |
| `helm_memory_index`         | 7           | 7                                   |
| `helm_personality`          | 6           | 6                                   |
| **Total**                   | **568**     | **568**                             |

Drill took ~10 minutes including docker image pull. Container torn down clean.

**Friction surfaced (now in the runbook):**

1. Stock `postgres:17` lacks pgvector — must use `pgvector/pgvector:pg17`.
2. Dump references `"extensions"."vector"` — the `extensions` schema must be pre-created with pgvector inside it (matches Supabase's layout).
3. Supabase RBAC roles (`anon`, `authenticated`, `service_role`) aren't on stock Postgres — GRANT statements fail with ~20 errors. Harmless; filter the output.

## Files changed

| File                                            | Change                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| `scripts/backup.sh`                             | NEW — cron-friendly full backup with 30-dump rotation.            |
| `docs/runbooks/0002-supabase-backup-restore.md` | NEW — second runbook in the repo, follows runbook 0001 structure. |

## Verification

- Drill succeeded (counts above)
- `mypy --strict .` (helm-runtime) → still clean (no Python source changes)
- `ruff` + `black` + `pre-commit` → clean
- `bash scripts/backup.sh` produces a valid 4.1 MB SQL file with 1329 lines

## Spec deviations (small, flagged)

1. **Backup uses `supabase db dump` instead of `pg_dump $SUPABASE_DB_URL`.** Same reasoning as T0.A7 / T0.A9: the supabase CLI reuses the existing project link, no separate Postgres URL needed. Output is functionally identical.

2. **Backup is two `supabase db dump` calls (data-only + schema), concatenated.** Single-call `supabase db dump` only emits data OR schema, not both. The script runs both then concatenates schema → data so `psql` replays cleanly (DDL before INSERTs).

3. **Drill done against local docker `pgvector/pgvector:pg17`, not "a test Supabase project."** Spec said test project. A throwaway docker is more reproducible (no Supabase branch lifecycle, no second-project provisioning, zero cloud cost), and the friction we surfaced is real ops knowledge that translates to either target. If the architect strongly prefers a fresh Supabase project for the formal STOP-gate confirmation, I can re-run; the drill template in the runbook works against either.

## Adjacent debt explicitly NOT in scope

- **Off-site backup automation.** Runbook documents this as Stage 2 work (GitHub Actions workflow uploading dumps to a bucket). Today: dumps live on Maxwell's laptop only. T1-acceptable per spec ("Manual + documented. T4.1 / Stage 2 considers automation").
- **Periodic CI restore drills.** Same — Stage 2 candidate. Runbook flags it under Prevention.
- **Migrations history table backup.** `supabase db dump --schema public` doesn't include `supabase_migrations.schema_migrations`. For the "restore to a fresh Supabase project" path, that's actually correct (you re-apply migrations via `supabase db push` afterward). For "this dump IS prod" it's a gap. Documented in "What's NOT backed up."

## What this unlocks

- **Real path back from "I broke the brain."** Drill-tested, not aspirational.
- **AGENTS.md hard rule 7** ("CI must be green before claiming ready") gets a sister rule in spirit: backups must be drill-tested before being trusted. The drill-log entry is the contract.
- **T0.A11 (Runtime Guardrails)** can rely on the backup path existing — guardrails that prevent budget incidents are paired with the backup path that recovers from data incidents.
- **Stage 2 deployment work (T4.x)** has a documented baseline for what "production-ready" data resilience looks like; CI-automated drills become an additive evolution, not a redesign.

Phase 0A pacing note: task 10 of ~15. Foundation arc (T0.A1–A10) closes here. Remaining Phase 0A: T0.A11 (runtime guardrails), T0.A12 (CI container build, ARCH), T0.A13 (gitleaks), T0.A14 (dependency automation, ARCH), T0.A15 (cost summary).

## STOP gate

Spec STOP-gate condition: "Maxwell confirms the restore drill works."

The drill ran end-to-end with verified counts (above). Two ways to confirm:

1. **Take the drill on its merits as documented** — counts match exactly, friction is captured, procedure is reproducible. Approve.
2. **Re-run the drill yourself** — the runbook's Path B is step-by-step and reproducible in ~10 minutes. Useful if you want hands-on confidence (recommended for the FIRST drill of a new procedure, optional thereafter).

After approval + merge, T0.A11 (runtime guardrails — rate alarm + dollar cap + Pro Max tracker) is next.
