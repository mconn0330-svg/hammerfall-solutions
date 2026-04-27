-- =============================================================
-- T0.B5 — helm_prompts Table
--
-- Supabase becomes the source of truth for agent system prompts.
-- On-disk files at services/helm-runtime/agents/prompts/<role>.md
-- are the boot-time fallback. PromptManager.load() tries Supabase
-- first; if Supabase is unreachable AND the file is missing, the
-- runtime refuses to boot (fail-loud, not fail-silent with stale).
--
-- One active version per agent role at a time. Push deactivates the
-- previous active row in a single transaction. Versions are kept
-- (not deleted) so prompt history is queryable for audit.
--
-- T0.B6 will add a SNAPSHOT header to the on-disk prompt files
-- marking them as mirrors of the canonical Supabase versions.
-- =============================================================

-- Reversibility: Class 2 (forward-only)
-- Per ADR-002: CREATE TABLE / CREATE INDEX / CREATE POLICY are
-- additive operations. No data is dropped or transformed; rollback
-- means dropping the new table (which loses prompt-version history
-- but no production behavior since file fallback always works).
-- DOWN section retained below as documentation, not required by policy.

CREATE TABLE IF NOT EXISTS helm_prompts (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_role    TEXT         NOT NULL,                -- e.g. 'helm_prime', 'projectionist'
  version       INT          NOT NULL,                -- monotonic per-role
  content       TEXT         NOT NULL,                -- prompt body
  active        BOOLEAN      NOT NULL DEFAULT true,
  pushed_by     TEXT,                                 -- audit: 'cli', 'maxwell', 'ci'
  pushed_from   TEXT,                                 -- 'file' | 'api' | 'manual'
  notes         TEXT,                                 -- optional commit-message-style note
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  -- Version is unique per agent role
  CONSTRAINT helm_prompts_unique_role_version UNIQUE (agent_role, version)
);

-- Partial unique index: at most one active prompt per agent role.
-- Push deactivates the previous active row in the same transaction so
-- this constraint always holds.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_prompt_per_role
  ON helm_prompts (agent_role)
  WHERE active = true;

-- Common query patterns
CREATE INDEX IF NOT EXISTS idx_helm_prompts_role_active
  ON helm_prompts (agent_role, active);

CREATE INDEX IF NOT EXISTS idx_helm_prompts_created_at
  ON helm_prompts (created_at DESC);

-- RLS — service role bypasses (consistent with all brain tables).
-- Anon read is enabled because the UI's Memory widget may surface
-- prompt history (read-only) at some point. Mutation stays server-side.
ALTER TABLE helm_prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON helm_prompts
  USING (true)
  WITH CHECK (true);

CREATE POLICY "anon_read_helm_prompts" ON helm_prompts
  FOR SELECT TO anon
  USING (true);

GRANT SELECT ON helm_prompts TO anon;
GRANT ALL ON helm_prompts TO service_role;

-- Class 2 (forward-only, additive). No DOWN block required per ADR-002.
-- To revert manually: drop the table + RLS policies + indexes. Loses prompt
-- history but no production behavior since the file fallback always works.
