-- =============================================================
-- JARVANA STAGE 0 — Schema Corrections Migration 002
-- Corrects gaps from migration 001:
--   - helm_beliefs: global model (drop project/agent), rename content→belief,
--     add source, updated_at, fix default strength, add indexes
--   - helm_entities: global model (drop project/agent), add summary/active,
--     rename created_at→first_seen, add last_updated, add indexes
--   - helm_personality: global model (drop project/agent), rename note→description,
--     add UNIQUE constraint, seed 6 default attributes
--   - helm_memory: add confidence FLOAT, subject_ref UUID FK
-- =============================================================

-- ---------------------------------------------------------------
-- 1. helm_beliefs — correct to global identity model
-- ---------------------------------------------------------------
ALTER TABLE helm_beliefs
  DROP COLUMN IF EXISTS project,
  DROP COLUMN IF EXISTS agent,
  DROP COLUMN IF EXISTS sync_ready;

-- Rename content → belief
ALTER TABLE helm_beliefs RENAME COLUMN content TO belief;

-- Add source and updated_at
ALTER TABLE helm_beliefs
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'seeded',
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Fix default strength from 0.9 → 0.7
ALTER TABLE helm_beliefs ALTER COLUMN strength SET DEFAULT 0.7;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_beliefs_domain   ON helm_beliefs(domain);
CREATE INDEX IF NOT EXISTS idx_beliefs_active   ON helm_beliefs(active);
CREATE INDEX IF NOT EXISTS idx_beliefs_strength ON helm_beliefs(strength);

-- ---------------------------------------------------------------
-- 2. helm_entities — correct to global identity model
-- ---------------------------------------------------------------
ALTER TABLE helm_entities
  DROP COLUMN IF EXISTS project,
  DROP COLUMN IF EXISTS agent,
  DROP COLUMN IF EXISTS sync_ready;

-- Add summary and active columns
ALTER TABLE helm_entities
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS active  BOOLEAN NOT NULL DEFAULT TRUE;

-- Rename created_at → first_seen, updated_at → last_updated
ALTER TABLE helm_entities RENAME COLUMN created_at  TO first_seen;
ALTER TABLE helm_entities RENAME COLUMN updated_at  TO last_updated;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entities_type ON helm_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON helm_entities(name);

-- ---------------------------------------------------------------
-- 3. helm_personality — correct to global identity model
-- ---------------------------------------------------------------
ALTER TABLE helm_personality
  DROP COLUMN IF EXISTS project,
  DROP COLUMN IF EXISTS agent;

-- Rename note → description
ALTER TABLE helm_personality RENAME COLUMN note TO description;

-- Add UNIQUE constraint on attribute
-- Add UNIQUE constraint (drop first to make idempotent)
ALTER TABLE helm_personality
  DROP CONSTRAINT IF EXISTS uq_personality_attribute;
ALTER TABLE helm_personality
  ADD CONSTRAINT uq_personality_attribute UNIQUE (attribute);

-- Drop created_at (spec has only updated_at on this table)
-- Leave it — it's harmless and useful for audit. Not dropping.

-- Seed default personality attributes (upsert — safe to re-run)
INSERT INTO helm_personality (attribute, score, description) VALUES
  ('directness',         0.9, '0=diplomatic/hedged, 1=BLUF always, no softening'),
  ('verbosity',          0.6, '0=minimal one-sentence, 1=full context always'),
  ('sarcasm',            0.3, '0=earnest always, 1=consistently sardonic'),
  ('formality',          0.4, '0=casual/colloquial, 1=highly formal/precise'),
  ('challenge_frequency',0.8, '0=agrees readily, 1=challenges every assertion'),
  ('show_reasoning',     0.7, '0=answer only, 1=always shows full reasoning chain')
ON CONFLICT (attribute) DO UPDATE
  SET score       = EXCLUDED.score,
      description = EXCLUDED.description,
      updated_at  = NOW();

-- ---------------------------------------------------------------
-- 4. helm_memory — add confidence and subject_ref FK
-- ---------------------------------------------------------------
ALTER TABLE helm_memory
  ADD COLUMN IF NOT EXISTS confidence  FLOAT
    CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
  ADD COLUMN IF NOT EXISTS subject_ref UUID;

ALTER TABLE helm_memory
  DROP CONSTRAINT IF EXISTS fk_subject;
ALTER TABLE helm_memory
  ADD CONSTRAINT fk_subject
    FOREIGN KEY (subject_ref) REFERENCES helm_entities(id);

-- =============================================================
-- Notes:
-- * sync_ready retained on helm_beliefs — beyond-spec addition,
--   harmless, dropped here for global model consistency.
--   Actually: dropping it above.
-- * source defaults to 'seeded' for all brain.sh writes.
--   learned/corrected values set by Phase 2 or direct DB update.
-- * helm_personality.created_at retained (useful audit trail).
-- * UNIQUE constraint on personality.attribute enforces one row
--   per attribute — upsert pattern handles updates.
-- =============================================================
