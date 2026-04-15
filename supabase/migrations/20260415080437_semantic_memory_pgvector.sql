-- Semantic Memory — pgvector + match_memories() RPC
-- Adds embedding support to helm_memory.
-- Stage 1 / S1-BA2: helm_memory only. helm_beliefs and helm_entities deferred to Stage 2.

-- Enable pgvector extension (idempotent — safe to run on already-enabled projects)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to helm_memory
-- vector(1536) matches text-embedding-3-small output dimensions
ALTER TABLE helm_memory ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- HNSW index for cosine similarity search
-- m=16, ef_construction=64: balanced default for most workloads
-- No training phase required (unlike IVFFlat) — safe to create before rows are populated
CREATE INDEX IF NOT EXISTS idx_helm_memory_embedding
  ON helm_memory
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- match_memories() — semantic similarity search for Helm memory entries
-- Called from supabase_client.py match_memories() method
-- Scoped to a single project/agent pair — no cross-project leakage
--
-- Parameters:
--   query_embedding  — the 1536-dim vector to search against
--   match_project    — project scope (e.g. 'hammerfall-solutions')
--   match_agent      — agent scope (e.g. 'helm')
--   match_threshold  — minimum cosine similarity (0.0–1.0, default 0.7)
--   match_count      — max rows returned (default 10)
--
-- Returns: id, project, agent, memory_type, content, session_date, created_at, similarity
-- Only rows where embedding IS NOT NULL are considered.
CREATE OR REPLACE FUNCTION match_memories(
  query_embedding vector(1536),
  match_project   text,
  match_agent     text,
  match_threshold float DEFAULT 0.7,
  match_count     int   DEFAULT 10
)
RETURNS TABLE (
  id           uuid,
  project      text,
  agent        text,
  memory_type  text,
  content      text,
  session_date date,
  created_at   timestamptz,
  similarity   float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    h.id,
    h.project,
    h.agent,
    h.memory_type,
    h.content,
    h.session_date,
    h.created_at,
    (1 - (h.embedding <=> query_embedding))::float AS similarity
  FROM helm_memory h
  WHERE h.project = match_project
    AND h.agent   = match_agent
    AND h.embedding IS NOT NULL
    AND (1 - (h.embedding <=> query_embedding)) > match_threshold
  ORDER BY h.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
