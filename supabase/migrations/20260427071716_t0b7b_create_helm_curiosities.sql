-- =============================================================
-- 20260427071716_t0b7b_create_helm_curiosities — Tier 2 brain types, sub-PR 2 of 3
--
-- Reversibility: Class 2
-- (CREATE TABLE; rollback = DROP TABLE. Forward-only by nature per ADR-002.)
--
-- Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.B7b
-- Brain types: docs/founding_docs/Helm_Brain_Object_Types.md §helm_curiosities
-- Arch one-pager: docs/stage1/arch_notes/T0.B7_tier2_brain_types.md
--                 (architect approved 2026-04-24)
--
-- Why this matters: helm_curiosities is the queue of open questions Helm
-- has formed but not resolved. Without it, Helm only responds — he never
-- drives. Curiosity is the substrate that makes T2 (scheduled passes)
-- actually do something. T3.5 hello-world's "Helm cares" 3-of-5 contract
-- requires "unprompted curiosity surface" — this table makes that real.
--
-- T0.B7b is also the abstraction-validation gate per the arch one-pager:
-- if adding this new type takes more than ~80 lines in the memory module
-- proper (target) or ~150 lines (fail-flag), T0.B1's abstraction failed
-- and gets revisited before T0.B7c.
--
-- Schema enrichments over the bare brain-types-doc sketch:
--   - id gets DEFAULT gen_random_uuid() (consistency with helm_entities,
--     helm_memory, helm_frames)
--   - status gets NOT NULL DEFAULT 'open' (curiosities are born open;
--     making it nullable creates "what does NULL status mean?" ambiguity)
--   - explicit indexes for the dominant access patterns
-- =============================================================

CREATE TABLE IF NOT EXISTS helm_curiosities (
  id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  project     TEXT         NOT NULL,
  agent       TEXT         NOT NULL DEFAULT 'helm',
  question    TEXT         NOT NULL,
  formed_from UUID         REFERENCES helm_memory(id) ON DELETE SET NULL,
  priority    TEXT         CHECK (priority IS NULL OR priority IN ('low', 'medium', 'high')),
  status      TEXT         NOT NULL DEFAULT 'open'
                           CHECK (status IN ('open', 'investigating', 'resolved', 'abandoned')),
  resolution  TEXT,
  formed_at   TIMESTAMPTZ  DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

-- Indexes for the dominant access patterns:
--   "open curiosities for this project, by priority" (Prime context loader)
--   "all curiosities sourced from this memory entry" (audit trail)
--   "recently formed curiosities" (Contemplator's reading list)
CREATE INDEX IF NOT EXISTS idx_curiosities_project_status
  ON helm_curiosities (project, status);

CREATE INDEX IF NOT EXISTS idx_curiosities_formed_from
  ON helm_curiosities (formed_from)
  WHERE formed_from IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_curiosities_formed_at
  ON helm_curiosities (formed_at DESC);

-- RLS — same pattern as the other helm_* tables: deny by default,
-- service_role gets full access (the runtime + scripts authenticate
-- as service_role). End-user-scoped policies arrive when productization
-- per-user brains land (Stage 4).
ALTER TABLE helm_curiosities ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_full_access ON helm_curiosities
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- =============================================================
-- Notes:
-- * formed_from has ON DELETE SET NULL (not CASCADE) — if the source
--   memory entry is deleted, the curiosity remains as an orphan with
--   formed_from=NULL. Curiosities outlive their triggers; CASCADE
--   would silently lose them.
-- * priority is nullable + CHECK-constrained when present. NULL means
--   "not yet prioritized" — a valid signal distinct from low/medium/high.
-- * Forward-only per ADR-002 Class 2. Rollback = DROP TABLE
--   helm_curiosities CASCADE. Backups available per
--   docs/runbooks/0002-supabase-backup-restore.md.
-- =============================================================
