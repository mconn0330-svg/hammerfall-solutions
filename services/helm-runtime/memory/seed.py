"""Brain seeding mechanism — Finding #010 resolution.

Replaces the bash seed scripts (`scripts/seed_entities.sh`,
`scripts/seed_relationships.sh`, `scripts/patch_entity_summaries.sh`) that
were retired in T0.B6 (when their dependency `brain.sh` was deleted).
The bash scripts are gone in this PR; this module is the new canonical
path for bootstrapping a brain from declarative content.

Design:

- **Declarative data**, not imperative scripts. Entity + relationship
  content lives in YAML files (`seed/<brain-name>/{entities,relationships}.yaml`),
  not in shell heredocs. The seed mechanism is content-agnostic: same code
  seeds Maxwell's brain, the demo sandbox brain, and any future per-user
  brain — only the data file changes.

- **Name-based references**, not UUID-based. Relationships reference
  entities by name, not by hard-coded UUID. The seed mechanism creates
  entities first, captures the brain-assigned UUIDs, then writes
  relationships using the captured map. Means data files are portable
  across brains (each brain assigns its own UUIDs).

- **3-state safety guard** (preserved from the bash predecessor):
  - 0 rows: clean slate, proceed
  - exactly expected count: already seeded, return without writing
  - between: partial state, raise — manual recovery needed

- **Goes through the memory module write helpers** — `write_helm_entity_record()`
  and `write_helm_entity_relationship_record()`. Inherits outbox-fallback,
  observability, and CHECK-constraint enforcement automatically.

Usage:

    # As CLI (see memory/__main__.py) — env: SUPABASE_BRAIN_URL + SUPABASE_BRAIN_SERVICE_KEY
    python -m memory seed-entities <path-to-entities.yaml>
    python -m memory seed-relationships <path-to-relationships.yaml>

    # As Python (T2.9 fixtures, demo sandbox admin endpoint, productization)
    from memory.seed import seed_entities_from_file, seed_relationships_from_file
    name_to_uuid = await seed_entities_from_file(client, writer, entities_path)
    count = await seed_relationships_from_file(client, writer, name_to_uuid, rels_path)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

import yaml

from observability import get_logger

from .writer import MemoryWriter

logger = get_logger("helm.memory.seed")


class SeedError(Exception):
    """Raised when seeding fails — bad YAML, partial state guard, or
    relationship references an unknown entity name."""


class _SelectCapable(Protocol):
    """Subset of ReadClient the safety guard needs (count rows in a table)."""

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...


# ─── YAML loaders ──────────────────────────────────────────────────────────


def load_entities_yaml(path: Path | str) -> list[dict[str, Any]]:
    """Parse an entities YAML file and return the entity list.

    Expected shape (single document):
        entities:
          - entity_type: person
            name: Maxwell Connolly
            aliases: [Max]
            attributes: {dob: "1988-08-23", ...}
            summary: "..."
          - ...

    Raises SeedError if the file is missing, malformed, or the top-level
    `entities:` key is absent.
    """
    path = Path(path)
    if not path.exists():
        raise SeedError(f"entities file not found: {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SeedError(f"YAML parse error in {path}: {e}") from e
    if not isinstance(doc, dict) or "entities" not in doc:
        raise SeedError(f"{path}: expected top-level `entities:` key")
    entities = doc["entities"]
    if not isinstance(entities, list):
        raise SeedError(f"{path}: `entities` must be a list, got {type(entities).__name__}")
    return entities


def load_relationships_yaml(path: Path | str) -> list[dict[str, Any]]:
    """Parse a relationships YAML file and return the relationship list.

    Expected shape (single document):
        relationships:
          - from: Maxwell Connolly
            to: Kimberly Connolly
            relationship: spouse
            notes: "..."
            confidence: 0.95
          - ...

    Raises SeedError if the file is missing, malformed, or the top-level
    `relationships:` key is absent.
    """
    path = Path(path)
    if not path.exists():
        raise SeedError(f"relationships file not found: {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SeedError(f"YAML parse error in {path}: {e}") from e
    if not isinstance(doc, dict) or "relationships" not in doc:
        raise SeedError(f"{path}: expected top-level `relationships:` key")
    rels = doc["relationships"]
    if not isinstance(rels, list):
        raise SeedError(f"{path}: `relationships` must be a list, got {type(rels).__name__}")
    return rels


# ─── Safety guard ──────────────────────────────────────────────────────────


async def _check_safety_guard(
    client: _SelectCapable,
    table: str,
    expected_count: int,
) -> str:
    """3-state guard — preserved from the bash seed scripts.

    Returns one of: "clean" (proceed with seed), "already_seeded" (exact
    expected count, return without writing), "partial" (caller should raise).
    """
    rows = await client.select(table, {"select": "id"})
    actual = len(rows)
    if actual == 0:
        return "clean"
    if actual == expected_count:
        return "already_seeded"
    return "partial"


# ─── Entity seeding ────────────────────────────────────────────────────────


async def seed_entities(
    client: _SelectCapable,
    writer: MemoryWriter,
    entities: list[dict[str, Any]],
) -> dict[str, UUID]:
    """Seed entities from a parsed list. Returns name → UUID map.

    The map is the pivot future relationship writes use to resolve names to
    the brain-assigned UUIDs. Caller passes this map to seed_relationships().

    Safety:
      - If `helm_entities` already has exactly `len(entities)` rows, returns
        the existing name → UUID map without writing (idempotent re-runs).
      - If `helm_entities` has 0 rows, writes all entities fresh.
      - If `helm_entities` has between 1 and `len(entities)-1` rows, raises
        SeedError — partial state is not safely resolvable by this script.
        Caller must clean up manually (or query for the partial set and
        skip those names in the data file).

    Each entity dict must have at minimum `entity_type` and `name`. Optional:
    `aliases`, `attributes`, `summary`, `salience_decay`, `embedding`.
    Unrecognized keys are ignored (forward-compat for new optional columns).
    """
    expected = len(entities)
    state = await _check_safety_guard(client, "helm_entities", expected)

    if state == "already_seeded":
        logger.info("seed.entities.already_seeded", expected=expected)
        existing = await client.select("helm_entities", {"select": "id,name"})
        return {row["name"]: UUID(row["id"]) for row in existing}

    if state == "partial":
        rows = await client.select("helm_entities", {"select": "id"})
        raise SeedError(
            f"helm_entities has {len(rows)} rows; expected 0 (clean) or {expected} "
            f"(fully seeded). Manual recovery needed: inspect helm_entities, remove "
            f"partial rows, then re-run."
        )

    # Clean slate — write all entities.
    name_to_uuid: dict[str, UUID] = {}
    for entry in entities:
        if "entity_type" not in entry or "name" not in entry:
            raise SeedError(f"entity entry missing required fields: {entry!r}")
        payload = await writer.write_helm_entity_record(
            entity_type=entry["entity_type"],
            name=entry["name"],
            aliases=entry.get("aliases"),
            attributes=entry.get("attributes"),
            summary=entry.get("summary"),
            salience_decay=entry.get("salience_decay"),
            embedding=entry.get("embedding"),
        )
        # The write_helm_entity_record return doesn't include the brain-
        # assigned id (it's the request payload, not the response). Re-query
        # by name to capture the id. Slight cost but the only way to learn
        # the assigned UUID since PostgREST insert returns nothing by default
        # in this code path. T-future optimization: have write_helm_entity_record
        # use Prefer: return=representation when callers need the id back.
        rows = await client.select(
            "helm_entities",
            {"name": f"eq.{payload['name']}", "select": "id", "limit": "1"},
        )
        if not rows:
            raise SeedError(
                f"entity {payload['name']!r} written but not found in subsequent SELECT"
            )
        name_to_uuid[payload["name"]] = UUID(rows[0]["id"])

    logger.info("seed.entities.written", count=len(name_to_uuid))
    return name_to_uuid


async def seed_entities_from_file(
    client: _SelectCapable,
    writer: MemoryWriter,
    path: Path | str,
) -> dict[str, UUID]:
    """File-loading wrapper around seed_entities()."""
    return await seed_entities(client, writer, load_entities_yaml(path))


# ─── Relationship seeding ──────────────────────────────────────────────────


async def seed_relationships(
    client: _SelectCapable,
    writer: MemoryWriter,
    name_to_uuid: dict[str, UUID],
    relationships: list[dict[str, Any]],
) -> int:
    """Seed relationships from a parsed list. Returns count written.

    Each relationship dict must have `from`, `to`, and `relationship` (label).
    Optional: `notes`, `confidence`, `active`.

    `from` and `to` are entity NAMES — resolved to UUIDs via name_to_uuid map
    (typically returned from a prior seed_entities() call).

    Safety: same 3-state guard as entities, on `helm_entity_relationships`.
    """
    expected = len(relationships)
    state = await _check_safety_guard(client, "helm_entity_relationships", expected)

    if state == "already_seeded":
        logger.info("seed.relationships.already_seeded", expected=expected)
        return 0

    if state == "partial":
        rows = await client.select("helm_entity_relationships", {"select": "id"})
        raise SeedError(
            f"helm_entity_relationships has {len(rows)} rows; expected 0 (clean) or "
            f"{expected} (fully seeded). Manual recovery needed."
        )

    written = 0
    for entry in relationships:
        for key in ("from", "to", "relationship"):
            if key not in entry:
                raise SeedError(f"relationship entry missing required field {key!r}: {entry!r}")
        from_name = entry["from"]
        to_name = entry["to"]
        if from_name not in name_to_uuid:
            raise SeedError(
                f"relationship references unknown from-entity {from_name!r}; "
                f"is it in the entities data file?"
            )
        if to_name not in name_to_uuid:
            raise SeedError(
                f"relationship references unknown to-entity {to_name!r}; "
                f"is it in the entities data file?"
            )
        await writer.write_helm_entity_relationship_record(
            from_entity=name_to_uuid[from_name],
            to_entity=name_to_uuid[to_name],
            relationship=entry["relationship"],
            notes=entry.get("notes"),
            confidence=entry.get("confidence"),
            active=entry.get("active", True),
        )
        written += 1

    logger.info("seed.relationships.written", count=written)
    return written


async def seed_relationships_from_file(
    client: _SelectCapable,
    writer: MemoryWriter,
    name_to_uuid: dict[str, UUID],
    path: Path | str,
) -> int:
    """File-loading wrapper around seed_relationships()."""
    return await seed_relationships(client, writer, name_to_uuid, load_relationships_yaml(path))
