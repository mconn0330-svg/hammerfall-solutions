-- =============================================================
-- JARVANA STAGE 0 — Gap Fixes Migration 003
-- 1. Add 'reasoning' to helm_memory.memory_type CHECK constraint
-- 2. Clean trailing newline from directness description in helm_personality
-- =============================================================

-- ---------------------------------------------------------------
-- 1. helm_memory.memory_type — add 'reasoning' to allowed values
-- Drop and recreate constraint (Postgres does not support ALTER CONSTRAINT)
-- ---------------------------------------------------------------
ALTER TABLE helm_memory DROP CONSTRAINT IF EXISTS helm_memory_memory_type_check;

ALTER TABLE helm_memory ADD CONSTRAINT helm_memory_memory_type_check
  CHECK (memory_type = ANY (ARRAY[
    'behavioral',
    'scratchpad',
    'archive',
    'sync',
    'monologue',
    'coherence_check',
    'external_knowledge',
    'reasoning'
  ]));

-- ---------------------------------------------------------------
-- 2. Clean trailing newline from directness description
-- ---------------------------------------------------------------
UPDATE helm_personality
  SET description = regexp_replace(description, '[\r\n]+$', '', 'g')
  WHERE attribute = 'directness';

-- =============================================================
