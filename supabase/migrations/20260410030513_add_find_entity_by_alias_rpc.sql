-- =============================================================
-- JARVANA STAGE 0 — find_entity_by_alias RPC Migration 006
-- Adds a Postgres function exposed as a Supabase RPC endpoint.
-- Provides case-insensitive entity lookup by name or alias.
--
-- Problem solved:
--   PostgREST's cs.{} (array contains) operator is case-sensitive
--   with no override flag. "Em" does not match "em". Storing aliases
--   in natural capitalised form (e.g. "Em", "Papa Shark") and doing
--   case-insensitive matching at the query layer via this function is
--   the correct architectural response.
--
-- Usage (called by Routine 4 duplicate guard, step 1+2):
--   POST /rest/v1/rpc/find_entity_by_alias
--   {"search_name": "emmy"}
--   Returns all helm_entities rows where LOWER(name) = LOWER(search_name)
--   OR any alias in the aliases array matches case-insensitively.
--
-- SECURITY DEFINER: runs with schema owner permissions, consistent
--   with service_role RLS policy on helm_entities.
-- STABLE: no side effects, result cacheable within a transaction.
--
-- Notes on attributes->>needs_alias_review=eq.true (Routine 0):
--   PostgREST's ->> operator returns text, so the comparison is against
--   the string "true", not the boolean. This works correctly because
--   Postgres coerces the JSON boolean to text "true" before PostgREST
--   evaluates it. Seed scripts must write needs_alias_review as a JSON
--   boolean (not a string) for this coercion to apply. Confirmed: brain.sh
--   passes --attributes as raw JSON, so {"needs_alias_review": true} is
--   written as a JSON boolean. Validate during Phase 1 QA by querying
--   Victor M after seeding and confirming he surfaces in the review queue.
-- =============================================================

CREATE OR REPLACE FUNCTION find_entity_by_alias(search_name TEXT)
RETURNS SETOF helm_entities AS $$
  SELECT * FROM helm_entities
  WHERE LOWER(name) = LOWER(search_name)
  OR EXISTS (
    SELECT 1 FROM unnest(aliases) AS a
    WHERE LOWER(a) = LOWER(search_name)
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- =============================================================
-- Grant execute to service_role so PostgREST can call it
-- =============================================================
GRANT EXECUTE ON FUNCTION find_entity_by_alias(TEXT) TO service_role;

-- =============================================================
-- Notes:
-- * OR logic: name match OR any alias match — one query covers both
--   Routine 4 step 1 (exact name) and step 2 (alias contains)
-- * active flag not filtered here — caller decides whether to filter
--   on active=true (Routine 4 should, to avoid matching retired entities)
-- * Returns SETOF — handles zero, one, or multiple matches cleanly
-- =============================================================
