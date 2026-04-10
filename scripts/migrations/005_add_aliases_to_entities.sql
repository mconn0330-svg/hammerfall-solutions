-- =============================================================
-- JARVANA STAGE 0 — Add Aliases to helm_entities Migration 005
-- Adds aliases TEXT[] column to helm_entities for tracking
-- alternate names, nicknames, and diminutives per entity.
--
-- GIN index required for performant array-contains queries:
--   helm_entities?aliases=cs.{Wes}
--
-- Used by the Routine 4 duplicate guard (3-step check):
--   Step 1 — exact name match (ilike)
--   Step 2 — alias array contains match (cs.{name})
--   Step 3 — contextual reasoning + confirmation prompt
--
-- Default value '{}' — existing rows unaffected.
-- =============================================================

ALTER TABLE helm_entities ADD COLUMN IF NOT EXISTS aliases TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_entities_aliases ON helm_entities USING GIN(aliases);

-- =============================================================
-- Notes:
-- * aliases are lowercase by convention — match is case-sensitive
--   at the PostgREST layer. Seed aliases in the exact form they
--   will appear in conversation.
-- * New aliases are appended via brain.sh --patch-id + --aliases
--   (full array replacement — caller reads current, appends, writes back)
-- * needs_alias_review flag in attributes surfaces entities with
--   unresolved name matches in the Routine 0 session-start check
-- =============================================================
