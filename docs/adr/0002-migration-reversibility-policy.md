# ADR 0002 — Migration reversibility policy

**Status:** Accepted
**Date:** 2026-04-25
**Deciders:** Maxwell McConnell (sole stakeholder), with architect input via T0.A9 spec

## Context

T0.A9 ("Migration Discipline + Schema Baseline") makes Supabase migrations a first-class artifact rather than ad-hoc SQL: numbered, idempotent where feasible, one logical change per file, and reversible where the operation warrants it.

"Where the operation warrants it" is the load-bearing clause. Every migration could in principle ship a `DOWN:` block, but most don't need one — adding an index, adding an RLS policy, creating a new table — these are forward-only by their nature; rolling them back is "just delete the table" and doesn't need a script. Other operations CAN'T be cleanly rolled back at all (data-destroying drops without a backup). The policy needs to draw the line so contributors know when a `DOWN:` is required, when it's optional, and when "irreversible — restore from backup" is the right thing to write.

This ADR draws that line.

## Decision

Each migration file in `supabase/migrations/` MUST include a header comment block declaring its reversibility class. The classes are:

### Class 1 — Reversible (DOWN section required)

Operations that can be cleanly undone with another SQL statement. The `DOWN:` block contains the SQL that reverses the migration.

**Triggers:**

- `DROP TABLE`, `DROP COLUMN`, `DROP INDEX`, `DROP CONSTRAINT`, `DROP TYPE`, `DROP POLICY`
- `ALTER TABLE ... RENAME`, `ALTER COLUMN ... RENAME`
- `ALTER COLUMN ... TYPE` (when the type change is lossy or not auto-castable)
- Any `UPDATE`/`DELETE`/`TRUNCATE` that mutates rows

**Required:** A `DOWN:` block with the exact SQL to restore the prior schema. The block is documentation — it is NOT auto-applied by the migration runner. It exists so the on-call human can run it manually if a deploy needs to roll back.

### Class 2 — Forward-only by nature (DOWN section optional)

Operations that add capability and have an obvious manual reversal but don't warrant scripting.

**Triggers:**

- `CREATE TABLE` (initial creation; rollback = `DROP TABLE`)
- `CREATE INDEX`, `CREATE UNIQUE INDEX` (rollback = `DROP INDEX`)
- `CREATE POLICY` (RLS additions; rollback = `DROP POLICY`)
- `CREATE OR REPLACE FUNCTION`, `CREATE FUNCTION` (rollback = `DROP FUNCTION` or replace with prior body)
- `ALTER TABLE ... ADD COLUMN` (where the column is nullable or has a default)

**Required:** A reversibility comment naming the class. No `DOWN:` block needed.

### Class 3 — Irreversible (explicit acknowledgement required)

Operations that destroy data such that no SQL can restore it.

**Triggers:**

- `DROP TABLE` containing rows that are not backed up elsewhere
- Lossy `ALTER COLUMN ... TYPE` (e.g., text → smaller varchar truncating values)
- `TRUNCATE` of a table that lacks a snapshot

**Required:** A `DOWN:` block containing the literal text `-- IRREVERSIBLE: restore from backup snapshot taken before this migration.` Plus a sentence in the migration's header comment naming the snapshot policy in effect at that time.

## Header comment format

Every migration begins with:

```sql
-- =============================================================
-- <YYYYMMDDHHMMSS>_<slug> — <one-line summary>
--
-- Reversibility: Class 1 | Class 2 | Class 3
-- (Class 1 only) DOWN section at end of file restores prior schema.
-- (Class 3 only) Snapshot taken: <date>, location: <where>
--
-- <Optional: longer context, why this change, what calls it.>
-- =============================================================
```

For Class 1 migrations, the file ends with:

```sql
-- =============================================================
-- DOWN:
-- (The SQL below would reverse this migration. Not auto-applied.
--  Run manually if rollback is needed.)
-- =============================================================
-- DROP TABLE ...;
-- ALTER TABLE ... RENAME COLUMN ... TO ...;
-- ...
```

The `DOWN:` block lives in SQL comments (every line begins with `--`) so it doesn't affect the forward migration; the `check_migration_reversibility.py` script parses the comment block.

## Consequences

- **Positive:**
  - Contributors don't have to think about whether their migration needs a rollback — the class triggers tell them.
  - Reviewers have a checkable artifact: does the file declare a class? If Class 1, is the DOWN block present? If Class 3, is the snapshot named?
  - On-call humans rolling back a deploy have the SQL right there in the migration file, not in someone's head or a separate runbook.
  - CI can mechanically enforce the policy via `scripts/check_migration_reversibility.py`.

- **Negative:**
  - Adds boilerplate to every migration. ~5 extra lines for Class 2, ~10 for Class 1 with the DOWN block.
  - "Did this need a DOWN block?" becomes a code-review question on every PR that touches migrations. The CI check catches the obvious cases but judgment calls (lossy ALTER COLUMN TYPE, in particular) still need a reviewer.
  - Existing 9 migrations (predating this ADR) lack the header. They're grandfathered — backfilling them is busywork, not value. New migrations comply.

- **Neutral / open:**
  - The reversibility script is intentionally simple — keyword detection on `DROP`, `ALTER ... RENAME`, `ALTER COLUMN ... TYPE`. False positives possible (e.g., `DROP INDEX` where the index was added in the same migration and is forward-only). False positives are easy to silence: declare Class 2 explicitly in the header. Better to over-flag than under-flag.

## Alternatives considered

- **No policy — trust contributors:** rejected. Single-dev project today; contributors-of-the-future is the failure mode. "I'll remember the DOWN" doesn't scale across months.
- **Auto-applied DOWN migrations (proper bidirectional like Rails/Django):** rejected. Supabase's migration tooling doesn't support down migrations natively; building it would be a significant detour. Documented `DOWN:` as comments achieves 90% of the value at 10% of the cost.
- **Snapshot-before-every-migration as the only rollback:** rejected. Snapshots are coarser than per-migration rollback — restoring loses everything since the snapshot. Documented `DOWN:` is more surgical.
- **Three-class policy as adopted, but auto-applied DOWN for Class 1:** considered. Rejected for the same reason as full bidirectional — supabase-cli doesn't help, and we'd be building scaffolding for a single-developer use case where the on-call human running one SQL block is fine.

## References

- Related ADRs: ADR 0001 (TypeScript conversion for helm-ui)
- Related spec sections: `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A9 (Migration Discipline + Schema Baseline)
- Related code: `scripts/migrate.sh`, `scripts/check_migration_reversibility.py`, `.github/workflows/migration-check.yml`
- Related runbooks: `docs/runbooks/0002-migration-rollback.md` (TBD — first time we need to actually roll one back)

---

_Format: [Michael Nygard ADR](https://github.com/joelparkerhenderson/architecture-decision-record/tree/main/locales/en/templates/decision-record-template-by-michael-nygard)._
