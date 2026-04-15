-- Semantic Embeddings — helm_beliefs and helm_entities
-- Stage 1 / S1-BA2b: extends pgvector coverage to beliefs and entities.
-- helm_memory coverage added in 20260415080437_semantic_memory_pgvector.sql.
--
-- Note: pgvector is installed in the extensions schema on this Supabase project.
-- All vector type references are schema-qualified (extensions.vector) to avoid
-- search_path-dependent type resolution failures.

-- ---------------------------------------------------------------
-- helm_beliefs — embed the belief text
-- ---------------------------------------------------------------

ALTER TABLE helm_beliefs ADD COLUMN IF NOT EXISTS embedding extensions.vector(1536);

CREATE INDEX IF NOT EXISTS helm_beliefs_embedding_idx
  ON helm_beliefs USING hnsw (embedding extensions.vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- match_beliefs() — semantic similarity search across Helm's belief system
--
-- Parameters:
--   query_embedding — the 1536-dim vector to search against
--   match_threshold — minimum cosine similarity (0.0–1.0, default 0.7)
--   match_count     — max rows returned (default 10)
--
-- Returns: id, domain, belief, strength, active, created_at, similarity
-- Only active beliefs with non-null embeddings are considered.
CREATE OR REPLACE FUNCTION match_beliefs(
  query_embedding extensions.vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count     int   DEFAULT 10
)
RETURNS TABLE (
  id         uuid,
  domain     text,
  belief     text,
  strength   float,
  active     boolean,
  created_at timestamptz,
  similarity float
)
LANGUAGE sql STABLE
SET search_path = extensions, public
AS $$
  SELECT
    id, domain, belief, strength, active, created_at,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_beliefs
  WHERE active = true
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- ---------------------------------------------------------------
-- helm_entities — embed name + summary (summary is the semantic anchor)
-- ---------------------------------------------------------------

ALTER TABLE helm_entities ADD COLUMN IF NOT EXISTS embedding extensions.vector(1536);

CREATE INDEX IF NOT EXISTS helm_entities_embedding_idx
  ON helm_entities USING hnsw (embedding extensions.vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- match_entities() — semantic similarity search across Helm's entity graph
--
-- Parameters:
--   query_embedding — the 1536-dim vector to search against
--   match_threshold — minimum cosine similarity (0.0–1.0, default 0.7)
--   match_count     — max rows returned (default 10)
--
-- Returns: id, entity_type, name, summary, attributes, first_seen, similarity
-- Only active entities with non-null embeddings are considered.
-- Note: helm_entities uses first_seen/last_updated, not created_at/updated_at.
CREATE OR REPLACE FUNCTION match_entities(
  query_embedding extensions.vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count     int   DEFAULT 10
)
RETURNS TABLE (
  id          uuid,
  entity_type text,
  name        text,
  summary     text,
  attributes  jsonb,
  first_seen  timestamptz,
  similarity  float
)
LANGUAGE sql STABLE
SET search_path = extensions, public
AS $$
  SELECT
    id, entity_type, name, summary, attributes, first_seen,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_entities
  WHERE active = true
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
