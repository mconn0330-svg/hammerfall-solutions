-- =============================================================
-- JARVANA STAGE 0 — Entity Relationships Migration 004
-- Adds helm_entity_relationships join table.
-- Connects entities in a directed graph: from_entity → to_entity
-- with a relationship label, optional notes, optional strength,
-- and an active flag for when relationships end.
--
-- Write sequence:
--   1. Create entity via helm_entities (brain.sh --table helm_entities)
--   2. Capture UUID from response
--   3. Write relationship referencing both UUIDs
--   No auto-lookup by name — caller resolves UUIDs before writing.
--
-- Bidirectionality convention:
--   Two rows per relationship. Labels change by perspective.
--   Maxwell → Kim: spouse    |  Kim → Maxwell: spouse
--   Maxwell → Emma: parent   |  Emma → Maxwell: child
--   Maxwell → Alexandria Township: resident  |  Alexandria Township → Maxwell: location
--
-- Relationship label conventions (not a constraint — documented for consistency):
--   People:   spouse, parent, child, sibling, friend, colleague, employer, employee
--   Places:   resident, workplace, origin
--   Concepts: creator, owner, contributor
--   Orgs:     member, founder, employee, client
-- =============================================================

CREATE TABLE IF NOT EXISTS helm_entity_relationships (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  from_entity  UUID        NOT NULL REFERENCES helm_entities(id),
  to_entity    UUID        NOT NULL REFERENCES helm_entities(id),
  relationship TEXT        NOT NULL,
  notes        TEXT,
  active       BOOLEAN     NOT NULL DEFAULT TRUE,
  strength     FLOAT       CHECK (strength IS NULL OR (strength >= 0.0 AND strength <= 1.0)),
  created_at   TIMESTAMPTZ DEFAULT NOW(),

  -- No self-relationships
  CONSTRAINT no_self_relationship CHECK (from_entity <> to_entity)
);

-- Indexes — make both directions of the graph fast
CREATE INDEX IF NOT EXISTS idx_rel_from   ON helm_entity_relationships(from_entity);
CREATE INDEX IF NOT EXISTS idx_rel_to     ON helm_entity_relationships(to_entity);
CREATE INDEX IF NOT EXISTS idx_rel_active ON helm_entity_relationships(active);

-- RLS
ALTER TABLE helm_entity_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_full_access ON helm_entity_relationships
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- =============================================================
-- Notes:
-- * active=false = retired relationship (never deleted, audit trail preserved)
-- * strength is nullable — absence of score is valid information
-- * relationship label is TEXT NOT NULL — no enum constraint intentional,
--   labels evolve as the entity graph grows
-- =============================================================
