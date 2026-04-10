-- =============================================================
-- HAMMERFALL BA5 — Patch Relationship Notes Trailing Newlines
--
-- Strips trailing \r and \n characters from all notes in
-- helm_entity_relationships. These were introduced by the
-- <<< heredoc operator on Windows/Git Bash in seed_relationships.sh,
-- same root cause as the entity name fix in patch_entity_summaries.sh.
--
-- One-shot data fix. Safe to re-apply (idempotent — RTRIM of already-
-- clean strings is a no-op).
-- =============================================================

UPDATE helm_entity_relationships
SET notes = REGEXP_REPLACE(notes, '[\r\n]+$', '')
WHERE notes IS NOT NULL
  AND notes ~ '[\r\n]+$';
