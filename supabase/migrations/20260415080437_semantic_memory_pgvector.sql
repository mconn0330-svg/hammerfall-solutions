-- Semantic Memory — pgvector + match_memories() RPC
-- Adds embedding support to helm_memory.
-- Stage 1 / S1-BA2: helm_memory only. helm_beliefs and helm_entities deferred to Stage 2.

-- Enable pgvector extension (idempotent — safe to run on already-enabled projects)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to helm_memory
-- vector(1536) matches text-embedding-3-small output dimensions
ALTER TABLE helm_memory ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- IVFFlat index for cosine similarity search
-- lists=100: standard default for up to ~1M rows
CREATE INDEX IF NOT EXISTS helm_memory_embedding_idx
  ON helm_memory USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- match_memories() — semantic similarity search for Helm memory entries
-- Called from supabase_client.py match_memories() method
-- Scoped to a single project/agent pair — no cross-project leakage
--
-- Parameters:
--   query_embedding — the 1536-dim vector to search against
--   match_threshold — minimum cosine similarity (0.0–1.0, default 0.7)
--   match_count     — max rows returned (default 10)
--   filter_project  — project scope (default 'hammerfall-solutions')
--   filter_agent    — agent scope (default 'helm')
--
-- Returns: id, content, memory_type, confidence, session_date, created_at, similarity
-- Only rows where embedding IS NOT NULL are considered.
CREATE OR REPLACE FUNCTION match_memories(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count     int   DEFAULT 10,
  filter_project  text  DEFAULT 'hammerfall-solutions',
  filter_agent    text  DEFAULT 'helm'
)
RETURNS TABLE (
  id           uuid,
  content      text,
  memory_type  text,
  confidence   float,
  session_date date,
  created_at   timestamptz,
  similarity   float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id, content, memory_type, confidence, session_date, created_at,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_memory
  WHERE project = filter_project
    AND agent   = filter_agent
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
