-- =============================================================
-- JARVANA STAGE 0 — Schema Migration 001
-- Adds helm_beliefs, helm_entities, helm_personality tables
-- and full_content JSONB column to helm_memory.
-- Run once against the hammerfall-brain Supabase project.
-- =============================================================

-- ---------------------------------------------------------------
-- 1. Extend helm_memory with full_content JSONB
-- ---------------------------------------------------------------
ALTER TABLE helm_memory ADD COLUMN IF NOT EXISTS full_content JSONB;

-- ---------------------------------------------------------------
-- 2. helm_beliefs — Helm's belief system
-- type arg maps to: domain (architecture, process, people, ethics, etc.)
-- content arg maps to: the belief statement
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS helm_beliefs (
  id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  project     TEXT        NOT NULL,
  agent       TEXT        NOT NULL,
  domain      TEXT        NOT NULL,
  content     TEXT        NOT NULL,
  strength    FLOAT       DEFAULT 0.9 CHECK (strength >= 0.0 AND strength <= 1.0),
  active      BOOLEAN     DEFAULT TRUE,
  sync_ready  BOOLEAN     DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------
-- 3. helm_entities — Structured entity representations
-- type arg maps to: entity_type (person, organization, concept, etc.)
-- content arg maps to: entity name
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS helm_entities (
  id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  project     TEXT        NOT NULL,
  agent       TEXT        NOT NULL,
  entity_type TEXT        NOT NULL,
  name        TEXT        NOT NULL,
  attributes  JSONB       DEFAULT '{}',
  sync_ready  BOOLEAN     DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------
-- 4. helm_personality — Six communication attributes
-- type arg maps to: attribute (directness, verbosity, sarcasm,
--                              formality, challenge_frequency, show_reasoning)
-- content arg maps to: optional note
-- score stored via --score flag
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS helm_personality (
  id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  project     TEXT        NOT NULL,
  agent       TEXT        NOT NULL,
  attribute   TEXT        NOT NULL,
  score       FLOAT       NOT NULL DEFAULT 0.5 CHECK (score >= 0.0 AND score <= 1.0),
  note        TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------
-- Notes:
-- * No vector/embedding columns — deferred to Stage 1 (pgvector)
-- * full_content is never indexed or searched — cold retrieval by id only
-- * helm_personality rows are upserted by attribute, not appended
-- * helm_beliefs active=false = retired belief (never deleted, audit trail preserved)
-- =============================================================
