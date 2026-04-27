-- =============================================================
-- 20260427032105_t0b7a_helm_entities_deepening — Tier 2 brain types, sub-PR 1 of 3
--
-- Reversibility: Class 1
-- DOWN section at end of file restores prior schema (per ADR-002).
--
-- Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.B7a
-- Arch one-pager: docs/stage1/arch_notes/T0.B7_tier2_brain_types.md
--                 (architect approved 2026-04-24)
--
-- This migration is a reconciliation between what the spec literally
-- prescribes and what the production schema already contains. The spec
-- was authored expecting a pre-T0.B7 baseline; reality is several
-- "deepening" columns shipped piecemeal in earlier work (entity_type,
-- aliases, attributes via migrations 003-005; helm_entity_relationships
-- via migration 004). The actual T0.B7a delta is therefore smaller than
-- the spec's literal SQL implies — three new columns, two renames for
-- spec-name alignment, one CHECK constraint, and CASCADE on the
-- relationship FKs. See the T0.B7a SITREP for the full reconciliation.
-- =============================================================

-- -----------------------------------------------------------------------------
-- helm_entities — column additions and renames
-- -----------------------------------------------------------------------------

-- Rename existing time columns to spec-aligned names. The semantic equivalence
-- is exact: first_seen captured "when did Helm first encounter this entity"
-- (= first_mentioned_at); last_updated captured "when was this row last
-- touched" which is identical in current usage to "when did Helm last
-- reference this entity" (= last_mentioned_at). RENAME COLUMN is atomic and
-- preserves all existing data + indexes.
ALTER TABLE helm_entities RENAME COLUMN first_seen TO first_mentioned_at;
ALTER TABLE helm_entities RENAME COLUMN last_updated TO last_mentioned_at;

-- New column: salience_decay. Default 1.0 (no decay). Stage 2 will implement
-- the actual decay logic; the column exists now so that work doesn't require
-- a migration, per arch note point 5.
ALTER TABLE helm_entities ADD COLUMN IF NOT EXISTS salience_decay FLOAT DEFAULT 1.0;

-- Add CHECK constraint on entity_type. Reconciliation note: the spec doc's
-- enum was (person, project, concept, place, organization, tool, event), but
-- production already contains 3 rows with entity_type='pet' (seeded in BA5).
-- Pets are first-class entities Helm tracks (Sanchez, Krieger, Keeley have
-- their own personal history in the brain). The spec list was incomplete;
-- 'pet' is added as the 8th allowed type. Helm_Brain_Object_Types.md is
-- updated in the same PR to reflect this.
ALTER TABLE helm_entities ADD CONSTRAINT helm_entities_entity_type_check
  CHECK (entity_type IN (
    'person', 'project', 'concept', 'place', 'organization', 'tool', 'event', 'pet'
  ));

-- -----------------------------------------------------------------------------
-- helm_entity_relationships — column rename + FK CASCADE
-- -----------------------------------------------------------------------------

-- Rename strength → confidence per spec. The semantic distinction matters:
-- belief.strength means "how strongly Helm holds this belief," while
-- relationship.confidence means "how sure Helm is the relationship exists."
-- Same name across two domains was a source of cognitive collision.
-- Existing CHECK constraint follows the rename automatically in Postgres.
ALTER TABLE helm_entity_relationships RENAME COLUMN strength TO confidence;

-- Add ON DELETE CASCADE to relationship FKs so deleting an entity tidies
-- up its relationships (currently a delete would either fail or leave
-- dangling FK references depending on session state). Spec calls for this
-- explicitly and it's a small but important data-integrity fix.
ALTER TABLE helm_entity_relationships
  DROP CONSTRAINT helm_entity_relationships_from_entity_fkey,
  ADD  CONSTRAINT helm_entity_relationships_from_entity_fkey
       FOREIGN KEY (from_entity) REFERENCES helm_entities(id) ON DELETE CASCADE;

ALTER TABLE helm_entity_relationships
  DROP CONSTRAINT helm_entity_relationships_to_entity_fkey,
  ADD  CONSTRAINT helm_entity_relationships_to_entity_fkey
       FOREIGN KEY (to_entity) REFERENCES helm_entities(id) ON DELETE CASCADE;

-- =============================================================
-- Notes:
-- * 'notes' and 'active' columns on helm_entity_relationships are kept as-is
--   (production-used pre-T0.B7a; spec doesn't mention them so they're
--   non-conflicting additive context).
-- * Backups available per docs/runbooks/0002-supabase-backup-restore.md if
--   the DOWN block below proves insufficient (it shouldn't — every change
--   in this migration is cleanly reversible).
-- =============================================================

-- =============================================================
-- DOWN:
-- (The SQL below would reverse this migration. Not auto-applied.
--  Run manually if rollback is needed. Order matters — reverse the
--  forward order: undo CASCADE first, then renames, then CHECK,
--  then column adds.)
-- =============================================================
--
-- -- 1. Restore non-CASCADE FKs on helm_entity_relationships.
-- ALTER TABLE helm_entity_relationships
--   DROP CONSTRAINT helm_entity_relationships_to_entity_fkey,
--   ADD  CONSTRAINT helm_entity_relationships_to_entity_fkey
--        FOREIGN KEY (to_entity) REFERENCES helm_entities(id);
--
-- ALTER TABLE helm_entity_relationships
--   DROP CONSTRAINT helm_entity_relationships_from_entity_fkey,
--   ADD  CONSTRAINT helm_entity_relationships_from_entity_fkey
--        FOREIGN KEY (from_entity) REFERENCES helm_entities(id);
--
-- -- 2. Reverse the column rename on helm_entity_relationships.
-- ALTER TABLE helm_entity_relationships RENAME COLUMN confidence TO strength;
--
-- -- 3. Drop the entity_type CHECK constraint.
-- ALTER TABLE helm_entities DROP CONSTRAINT helm_entities_entity_type_check;
--
-- -- 4. Drop the new salience_decay column.
-- ALTER TABLE helm_entities DROP COLUMN salience_decay;
--
-- -- 5. Reverse the column renames on helm_entities.
-- ALTER TABLE helm_entities RENAME COLUMN last_mentioned_at TO last_updated;
-- ALTER TABLE helm_entities RENAME COLUMN first_mentioned_at TO first_seen;
