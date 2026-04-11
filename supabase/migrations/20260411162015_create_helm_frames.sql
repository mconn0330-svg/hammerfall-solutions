-- =============================================================
-- HAMMERFALL BA6d — helm_frames Table + memory_type Constraint
--
-- Pre-flight migration. Must ship before BA6a agent contracts.
--
-- PART 1: helm_frames
--   Projectionist's transient conveyor workspace.
--   Warm frames live here. Archivist migrates cold frames to
--   helm_memory at full fidelity, then deletes the row.
--   helm_frames is never the authoritative store — helm_memory is.
--
-- PART 2: helm_memory memory_type constraint normalization
--   reasoning and heartbeat are already in active production use
--   but absent from the original CHECK constraint. This closes
--   that gap. frame is new — added for BA6 frame storage.
-- =============================================================

-- =============================================================
-- PART 1 — helm_frames
-- =============================================================

CREATE TABLE helm_frames (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   UUID        NOT NULL,
  turn_number  INT         NOT NULL,
  layer        TEXT        NOT NULL DEFAULT 'warm'
                           CHECK (layer IN ('hot', 'warm', 'cold')),
  frame_json   JSONB       NOT NULL,
  frame_status TEXT        NOT NULL DEFAULT 'active'
                           CHECK (frame_status IN ('active', 'superseded', 'canonical')),
  created_at   TIMESTAMPTZ DEFAULT NOW(),

  -- Duplicate guard at the DB layer.
  -- If Projectionist accidentally writes the same turn twice,
  -- Supabase rejects it — no silent data corruption.
  UNIQUE (session_id, turn_number)
);

-- Primary query pattern: Projectionist fetching warm frames for a session in order
CREATE INDEX idx_helm_frames_session_turn ON helm_frames(session_id, turn_number);

-- Layer filter: Archivist reads layer='cold', Projectionist reads layer='warm'
CREATE INDEX idx_helm_frames_layer ON helm_frames(layer);

-- Session lookup without turn ordering
CREATE INDEX idx_helm_frames_session ON helm_frames(session_id);

-- RLS — service role bypasses all policies (consistent with all other brain tables)
ALTER TABLE helm_frames ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON helm_frames
  USING (true)
  WITH CHECK (true);

-- =============================================================
-- PART 2 — helm_memory memory_type constraint normalization
--
-- Drop and recreate to add:
--   reasoning    — already in active production use (brain.sh --confidence)
--   heartbeat    — already in active production use (10-message heartbeat)
--   frame        — new in BA6 for frame storage
-- =============================================================

ALTER TABLE helm_memory
  DROP CONSTRAINT IF EXISTS helm_memory_memory_type_check;

ALTER TABLE helm_memory
  ADD CONSTRAINT helm_memory_memory_type_check
  CHECK (memory_type IN (
    'behavioral',
    'scratchpad',
    'archive',
    'sync',
    'monologue',
    'coherence_check',
    'external_knowledge',
    'reasoning',
    'heartbeat',
    'frame'
  ));

-- =============================================================
-- Notes:
-- * helm_frames rows are deleted by Archivist after migration to
--   helm_memory. The table should be near-empty between sessions.
-- * frame_status appears as both a column (for queryability) and
--   a field inside frame_json (for full-fidelity archival).
--   Projectionist must update both in a single PATCH — never one
--   without the other. The column is authoritative for queries.
-- * superseded_reason and superseded_at_turn live inside frame_json
--   only — not top-level columns. Intentional: they are frame
--   payload metadata, not query targets at this stage.
-- * UNIQUE(session_id, turn_number) is the belt-and-suspenders
--   guard. Projectionist behavioral contract is the primary guard.
-- =============================================================
