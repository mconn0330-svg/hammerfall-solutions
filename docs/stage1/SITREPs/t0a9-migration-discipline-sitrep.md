# SITREP — T0.A9 Migration Discipline + Schema Baseline

**Date:** 2026-04-25
**Branch:** `feature/t0a9-migration-discipline`
**Tier:** STOP
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A9 (lines 654–712)

## Scope executed

Four of five spec deliverables ship in this PR. The fifth (schema baseline file) needs Maxwell-side DB access — flagged below as the one human step required.

| Deliverable                                | Status                                                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| ADR-002 (Migration Reversibility Policy)   | ✅ `docs/adr/0002-migration-reversibility-policy.md`                                                                |
| Migration discipline rules                 | ✅ codified in ADR-002 (header format, three classes, DOWN: spec)                                                   |
| `scripts/migrate.sh`                       | ✅ wraps supabase CLI for push / verify / baseline-dump                                                             |
| `scripts/check_migration_reversibility.py` | ✅ enforces ADR-002, grandfathers pre-cutoff migrations                                                             |
| `.github/workflows/migration-check.yml`    | ✅ runs reversibility check on every migration-touching PR; ephemeral-branch apply gated behind a project-tier flag |
| `supabase/schema_baseline.sql`             | ⏳ requires Maxwell to run `bash scripts/migrate.sh baseline-dump` (see "Maxwell-side step" below)                  |

## Files changed

| File                                              | Change                                                                                                                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/adr/0002-migration-reversibility-policy.md` | NEW — three-class policy: Class 1 (DOWN required), Class 2 (forward-only by nature), Class 3 (irreversible, restore-from-backup). Header format + DOWN block format documented.                             |
| `scripts/migrate.sh`                              | NEW — `push` / `verify` / `baseline-dump` subcommands. Uses `supabase db dump --schema public` for baseline (not raw `pg_dump $SUPABASE_DB_URL`); see deviation #1 below.                                   |
| `scripts/check_migration_reversibility.py`        | NEW — walks `supabase/migrations/`, enforces ADR-002. Grandfathers files with timestamp ≤ `20260425000000`. mypy --strict clean.                                                                            |
| `.github/workflows/migration-check.yml`           | NEW — separate workflow (not in `ci.yml`); only runs when migrations or the check script change. Two jobs: `reversibility` (always runs) + `apply-and-verify` (gated on `vars.SUPABASE_BRANCHING_ENABLED`). |

## Verification

- `python3 scripts/check_migration_reversibility.py supabase/migrations/` → **PASSED (9 file(s) scanned)** — all existing migrations are pre-cutoff and grandfathered
- `mypy --strict scripts/check_migration_reversibility.py` → 0 errors
- `mypy --strict .` (helm-runtime) → still clean
- `ruff check .` + `black --check .` → clean
- `pre-commit run` → clean (prettier reformatted ADR; restaged; clean)

## Spec deviations (small, flagged)

1. **`supabase db dump --schema public` instead of `pg_dump $SUPABASE_DB_URL --schema-only --schema=public`.** The Supabase CLI reuses the existing project link and doesn't need a separate Postgres URL or local pg_dump install. Output is the same shape. Spec gets noted in `migrate.sh` comments along with the `pg_dump` fallback.

2. **`apply-and-verify` job gated on `vars.SUPABASE_BRANCHING_ENABLED == 'true'`.** Supabase ephemeral branches require the Pro tier. We don't know yet whether the project is on Pro; rather than have CI fail confusingly, the job is opt-in via a repo variable. Reversibility check (the cheaper, always-valuable one) runs unconditionally. Maxwell sets `SUPABASE_BRANCHING_ENABLED=true` (repo variable) when the project is on Pro and `SUPABASE_ACCESS_TOKEN` is in secrets.

3. **Reversibility script grandfathers pre-T0.A9 migrations** (timestamp ≤ `20260425000000`). The 9 existing files predate the policy and don't have headers; backfilling them is busywork. New migrations from T0.A9 onward must declare a class. Documented in ADR-002 "Negative consequences."

## Maxwell-side step (required before merge OR as a follow-up)

The schema baseline file (`supabase/schema_baseline.sql`) needs to be generated against the live Supabase project. Two paths:

**Option A — generate now, commit to this branch:**

```bash
# Prerequisite: supabase CLI logged in, project linked
bash scripts/migrate.sh baseline-dump
git add supabase/schema_baseline.sql
git commit -m "chore(migration): add initial schema baseline (T0.A9)"
git push
```

**Option B — merge this PR without the baseline, ship it as a follow-up `chore(migration)` PR.** Same procedure, different branch.

The infrastructure ships either way; the baseline file is a snapshot of the current live schema and only Maxwell can produce it.

## Adjacent debt explicitly NOT in scope

- **Backfilling reversibility headers on existing 9 migrations.** Grandfathered by design (per ADR-002 negative-consequences section). Busywork without value.
- **`docs/runbooks/0002-migration-rollback.md`.** ADR-002 references it as TBD. Lands the first time we actually need to roll one back — until then, the runbook would be hypothetical.
- **Auto-applied DOWN migrations (Rails/Django-style bidirectional).** Considered and rejected in ADR-002. Supabase tooling doesn't natively support it; the comment-block approach achieves 90% of the value at 10% of the cost.
- **Tests for `check_migration_reversibility.py`.** Smoke-tested manually against the live 9 migrations (passed). Pytest unit tests are reasonable to add later, but writing them now would be premature for an operator-only tool. T0.B1 onward will exercise it on real PRs.

## What this unlocks

- **Every new migration is reviewable against a rule.** Reviewer asks: "what class? if Class 1, where's the DOWN?" — instead of "is this safe to ship?" judgment from scratch.
- **CI catches missing DOWN blocks** on PRs that touch migrations. Reversibility check is fast (sub-second) and runs on every relevant PR.
- **Schema baseline + per-migration deltas** = "rebuild from scratch" is `psql < schema_baseline.sql && supabase db push`. No more "the schema is whatever Supabase has right now."
- **T0.A10 (Backup + restore runbook)** has the schema-dump command pattern to reuse.
- **T0.B1+ (memory module)** lands new migrations under the policy from day one — pattern is set, no late-game retrofit.

Phase 0A pacing note: task 9 of ~15. Two more ARCH-tier tasks queued (T0.A12, T0.A14 at minimum); the rest are STOP/Batch.

## STOP gate

Standing by for your explicit approval. Two questions for the gate:

1. **Did you want to run the baseline dump now (so it lands in this PR), or as a follow-up `chore(migration)` PR after merge?** Either is fine; the deliverable shape is identical.
2. **Do you know whether the Supabase project is on Pro tier (branching available)?** If yes, set the `SUPABASE_BRANCHING_ENABLED` repo variable and add `SUPABASE_ACCESS_TOKEN` to secrets. If no, the apply-and-verify job stays opt-out and we revisit at T4.x.

After approval + merge (and the baseline file), T0.A10 (backup + restore runbook) is the next infrastructure beat.
