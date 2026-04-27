-- =============================================================
-- 20260427060825_hotfix_match_entities_first_mentioned_at — fix RPC fallout from T0.B7a
--
-- Reversibility: Class 1
-- DOWN section at end of file restores prior schema (per ADR-002).
--
-- Why: T0.B7a renamed helm_entities.first_seen → first_mentioned_at. The
-- match_entities RPC body still referenced first_seen. PostgreSQL does NOT
-- auto-rewrite SQL function bodies on column rename — function bodies are
-- stored as text, not bound to schema. The RPC has been broken in
-- production since the T0.B7a migration applied (semantic search across
-- helm_entities errors with `column "first_seen" does not exist`).
--
-- This migration recreates match_entities with the new column name in
-- both the RETURNS TABLE shape and the SELECT body.
--
-- Why DROP + CREATE (not CREATE OR REPLACE): the RETURNS TABLE column is
-- renamed (first_seen → first_mentioned_at). Postgres rejects
-- CREATE OR REPLACE when the OUT-parameter shape changes — `cannot change
-- return type of existing function`. DROP + CREATE is the documented fix.
--
-- Caller impact: read_client.py:match_entities() Python wrapper (and any
-- future callers) start working again immediately on apply. No call-site
-- code change needed because the RPC's parameter signature is unchanged
-- and the returned column name is still semantically equivalent.
--
-- This is also the kind of audit gap that should be caught by a regression
-- test — added in the same hotfix PR (services/helm-runtime/tests/agents/
-- test_contemplator.py asserts the live query column name).
-- =============================================================

DROP FUNCTION IF EXISTS match_entities(extensions.vector, float, int);

CREATE FUNCTION match_entities(
  query_embedding extensions.vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count     int   DEFAULT 10
)
RETURNS TABLE (
  id                  uuid,
  entity_type         text,
  name                text,
  summary             text,
  attributes          jsonb,
  first_mentioned_at  timestamptz,
  similarity          float
)
LANGUAGE sql STABLE
SET search_path = extensions, public
AS $$
  SELECT
    id, entity_type, name, summary, attributes, first_mentioned_at,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_entities
  WHERE active = true
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- =============================================================
-- Notes:
-- * The RETURNS TABLE column is renamed first_seen → first_mentioned_at.
--   Callers that destructure the result by position are unaffected;
--   callers that destructure by name need to use the new key. The Python
--   wrapper at services/helm-runtime/read_client.py:match_entities()
--   passes through the dict unchanged, so call sites consuming the dict
--   inherit the new key name automatically.
-- =============================================================

-- =============================================================
-- DOWN:
-- (The SQL below would reverse this migration. Not auto-applied.
--  Run manually if rollback is needed. The "rollback" recreates the
--  pre-hotfix function — which references the renamed-away first_seen
--  column and is broken by construction. Only useful if T0.B7a is
--  also rolled back to restore first_seen.)
-- =============================================================
--
-- DROP FUNCTION IF EXISTS match_entities(extensions.vector, float, int);
--
-- CREATE FUNCTION match_entities(
--   query_embedding extensions.vector(1536),
--   match_threshold float DEFAULT 0.7,
--   match_count     int   DEFAULT 10
-- )
-- RETURNS TABLE (
--   id          uuid,
--   entity_type text,
--   name        text,
--   summary     text,
--   attributes  jsonb,
--   first_seen  timestamptz,
--   similarity  float
-- )
-- LANGUAGE sql STABLE
-- SET search_path = extensions, public
-- AS $$
--   SELECT
--     id, entity_type, name, summary, attributes, first_seen,
--     1 - (embedding <=> query_embedding) AS similarity
--   FROM helm_entities
--   WHERE active = true
--     AND embedding IS NOT NULL
--     AND 1 - (embedding <=> query_embedding) > match_threshold
--   ORDER BY embedding <=> query_embedding
--   LIMIT match_count;
-- $$;
