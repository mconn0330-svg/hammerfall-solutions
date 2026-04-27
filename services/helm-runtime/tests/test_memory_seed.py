"""Tests for memory.seed — Finding #010 mechanism replacing the deleted
bash seed scripts.

Uses the synthetic fixtures at seed/example/ as the input data — they're
checked into the repo specifically so this test suite has a stable target
that mirrors real-world authoring shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from memory.seed import (
    SeedError,
    load_entities_yaml,
    load_relationships_yaml,
    seed_entities,
    seed_relationships,
)
from memory.writer import MemoryWriter

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_ENTITIES = REPO_ROOT / "seed" / "example" / "entities.yaml"
EXAMPLE_RELATIONSHIPS = REPO_ROOT / "seed" / "example" / "relationships.yaml"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures — recording client (writer + select) with optional pre-populated rows
# ──────────────────────────────────────────────────────────────────────────────


class _RecordingClient:
    """Stand-in for both MemoryClient (insert) and ReadClient (select).

    insert: appends to .calls and returns the payload (mirrors the real
    MemoryClient.insert shape).
    select: returns whatever is in .table_rows for the given table, optionally
    filtering by a single eq.<value> on `name`. Just enough to drive the
    seed mechanism's safety guard + name → UUID resolution.
    """

    def __init__(self, table_rows: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.table_rows: dict[str, list[dict[str, Any]]] = table_rows or {}

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((table, payload))
        # Simulate Supabase assigning an id and persisting the row so subsequent
        # SELECTs see it (the seed mechanism does a SELECT after each entity
        # insert to capture the brain-assigned UUID).
        persisted = {**payload, "id": str(uuid4())}
        self.table_rows.setdefault(table, []).append(persisted)
        return payload

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows = list(self.table_rows.get(table, []))
        # Honor a single name=eq.<value> filter (the only filter the seed
        # mechanism uses on the helm_entities post-insert lookup).
        name_filter = params.get("name")
        if isinstance(name_filter, str) and name_filter.startswith("eq."):
            wanted = name_filter[len("eq.") :]
            rows = [r for r in rows if r.get("name") == wanted]
        return rows


@pytest.fixture
def writer_and_client() -> tuple[MemoryWriter, _RecordingClient]:
    rec = _RecordingClient()
    w = MemoryWriter(rec)  # type: ignore[arg-type]
    return w, rec


# ──────────────────────────────────────────────────────────────────────────────
# YAML loaders — happy path + error paths
# ──────────────────────────────────────────────────────────────────────────────


def test_load_entities_yaml_parses_example_fixture() -> None:
    """The shipped example file parses to a list of dicts with the expected
    shape. If this fails, either the example is broken or the loader's
    schema expectations drifted."""
    entities = load_entities_yaml(EXAMPLE_ENTITIES)
    assert isinstance(entities, list)
    assert len(entities) == 5
    assert all("entity_type" in e and "name" in e for e in entities)
    # Spot-check known content from the fixture
    assert entities[0]["name"] == "Sample Person Alice"
    assert entities[0]["entity_type"] == "person"


def test_load_relationships_yaml_parses_example_fixture() -> None:
    rels = load_relationships_yaml(EXAMPLE_RELATIONSHIPS)
    assert isinstance(rels, list)
    assert len(rels) == 3
    assert all("from" in r and "to" in r and "relationship" in r for r in rels)
    assert rels[0]["from"] == "Sample Person Alice"


def test_load_entities_yaml_missing_file_raises_seed_error(tmp_path: Path) -> None:
    with pytest.raises(SeedError, match="not found"):
        load_entities_yaml(tmp_path / "nonexistent.yaml")


def test_load_entities_yaml_missing_top_level_key_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("some_other_key: []\n", encoding="utf-8")
    with pytest.raises(SeedError, match="entities"):
        load_entities_yaml(bad)


def test_load_relationships_yaml_missing_top_level_key_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("not_relationships: []\n", encoding="utf-8")
    with pytest.raises(SeedError, match="relationships"):
        load_relationships_yaml(bad)


def test_load_entities_yaml_top_level_must_be_list(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("entities: not_a_list\n", encoding="utf-8")
    with pytest.raises(SeedError, match="must be a list"):
        load_entities_yaml(bad)


def test_load_entities_yaml_malformed_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("entities: [\n  - unclosed", encoding="utf-8")
    with pytest.raises(SeedError, match="parse error"):
        load_entities_yaml(bad)


# ──────────────────────────────────────────────────────────────────────────────
# seed_entities — clean slate, already-seeded, partial state, payload shape
# ──────────────────────────────────────────────────────────────────────────────


async def test_seed_entities_clean_slate_writes_all(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Clean slate (table empty) → write every entity, return name → UUID map."""
    w, rec = writer_and_client
    entities = load_entities_yaml(EXAMPLE_ENTITIES)

    name_to_uuid = await seed_entities(rec, w, entities)

    # All 5 example entities written
    insert_calls = [c for c in rec.calls if c[0] == "helm_entities"]
    assert len(insert_calls) == 5
    # Map covers all entities
    assert set(name_to_uuid.keys()) == {e["name"] for e in entities}
    # All values are UUID instances (not strings)
    assert all(isinstance(v, UUID) for v in name_to_uuid.values())


async def test_seed_entities_already_seeded_returns_existing_map(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """If table already has exactly the expected count, return existing
    name → UUID map without writing. Idempotent re-run support."""
    w, rec = writer_and_client
    entities = load_entities_yaml(EXAMPLE_ENTITIES)

    # Pre-populate the table with rows matching the entity count
    existing_uuids = [str(uuid4()) for _ in entities]
    rec.table_rows["helm_entities"] = [
        {"id": uid, "name": e["name"]} for uid, e in zip(existing_uuids, entities, strict=True)
    ]

    name_to_uuid = await seed_entities(rec, w, entities)

    # No insert calls — already-seeded path
    insert_calls = [c for c in rec.calls if c[0] == "helm_entities"]
    assert insert_calls == []
    # Map populated from the existing rows
    assert set(name_to_uuid.keys()) == {e["name"] for e in entities}


async def test_seed_entities_partial_state_raises(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """1 ≤ existing rows < expected → SeedError (manual recovery needed)."""
    w, rec = writer_and_client
    entities = load_entities_yaml(EXAMPLE_ENTITIES)

    # Pre-populate with FEWER rows than expected
    rec.table_rows["helm_entities"] = [
        {"id": str(uuid4()), "name": entities[0]["name"]},
        {"id": str(uuid4()), "name": entities[1]["name"]},
    ]

    with pytest.raises(SeedError, match="Manual recovery needed"):
        await seed_entities(rec, w, entities)


async def test_seed_entities_missing_required_field_raises(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Each entity dict must have entity_type + name. Missing either is a
    SeedError before any partial writes go through."""
    w, rec = writer_and_client
    bad_entities = [{"name": "no type"}]  # missing entity_type

    with pytest.raises(SeedError, match="missing required fields"):
        await seed_entities(rec, w, bad_entities)


async def test_seed_entities_payload_shape_matches_writer_signature(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """The seed mechanism passes entity fields through to
    write_helm_entity_record. Verify the exact payload shape that lands
    in the helm_entities insert."""
    w, rec = writer_and_client
    entities = [
        {
            "entity_type": "person",
            "name": "Test Person",
            "aliases": ["TP"],
            "attributes": {"role": "test"},
            "summary": "A person used in tests.",
            "salience_decay": 0.8,
        }
    ]

    await seed_entities(rec, w, entities)

    insert = rec.calls[0]
    assert insert[0] == "helm_entities"
    payload = insert[1]
    assert payload["entity_type"] == "person"
    assert payload["name"] == "Test Person"
    assert payload["aliases"] == ["TP"]
    assert payload["attributes"] == {"role": "test"}
    assert payload["summary"] == "A person used in tests."
    assert payload["salience_decay"] == 0.8


# ──────────────────────────────────────────────────────────────────────────────
# seed_relationships — clean slate, already-seeded, partial, missing-name
# ──────────────────────────────────────────────────────────────────────────────


async def test_seed_relationships_clean_slate_writes_all_with_resolved_uuids(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Clean slate → write all 3 example relationships with UUIDs resolved
    from the supplied name → UUID map."""
    w, rec = writer_and_client
    rels = load_relationships_yaml(EXAMPLE_RELATIONSHIPS)
    name_to_uuid = {
        "Sample Person Alice": uuid4(),
        "Sample Person Bob": uuid4(),
        "Sample Place": uuid4(),
        "Sample Organization": uuid4(),
        "Sample Project": uuid4(),
    }

    count = await seed_relationships(rec, w, name_to_uuid, rels)

    assert count == 3
    insert_calls = [c for c in rec.calls if c[0] == "helm_entity_relationships"]
    assert len(insert_calls) == 3
    # First relationship in fixture is Alice → Bob 'friend'
    first_payload = insert_calls[0][1]
    assert first_payload["from_entity"] == str(name_to_uuid["Sample Person Alice"])
    assert first_payload["to_entity"] == str(name_to_uuid["Sample Person Bob"])
    assert first_payload["relationship"] == "friend"


async def test_seed_relationships_unknown_name_raises_with_helpful_message(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """If a relationship references an entity not in the name → UUID map,
    SeedError with a message pointing at the entities file. Catches typos
    and missing-entity authoring bugs early."""
    w, rec = writer_and_client
    rels = [{"from": "Unknown Entity", "to": "Other", "relationship": "friend"}]
    name_to_uuid = {"Other": uuid4()}

    with pytest.raises(SeedError, match="unknown from-entity"):
        await seed_relationships(rec, w, name_to_uuid, rels)


async def test_seed_relationships_unknown_to_entity_raises(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer_and_client
    rels = [{"from": "Known", "to": "Unknown", "relationship": "friend"}]
    name_to_uuid = {"Known": uuid4()}

    with pytest.raises(SeedError, match="unknown to-entity"):
        await seed_relationships(rec, w, name_to_uuid, rels)


async def test_seed_relationships_missing_required_field_raises(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer_and_client
    rels = [{"from": "A", "relationship": "friend"}]  # missing 'to'

    with pytest.raises(SeedError, match="missing required field 'to'"):
        await seed_relationships(rec, w, {"A": uuid4()}, rels)


async def test_seed_relationships_already_seeded_returns_zero(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Idempotent re-run: existing count == expected → return 0 without writing."""
    w, rec = writer_and_client
    rels = load_relationships_yaml(EXAMPLE_RELATIONSHIPS)
    rec.table_rows["helm_entity_relationships"] = [{"id": str(uuid4())} for _ in rels]
    name_to_uuid = {
        "Sample Person Alice": uuid4(),
        "Sample Person Bob": uuid4(),
        "Sample Place": uuid4(),
        "Sample Organization": uuid4(),
        "Sample Project": uuid4(),
    }

    count = await seed_relationships(rec, w, name_to_uuid, rels)

    assert count == 0
    inserts = [c for c in rec.calls if c[0] == "helm_entity_relationships"]
    assert inserts == []


async def test_seed_relationships_partial_state_raises(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer_and_client
    rels = load_relationships_yaml(EXAMPLE_RELATIONSHIPS)
    # Pre-populate with one row — partial state
    rec.table_rows["helm_entity_relationships"] = [{"id": str(uuid4())}]
    name_to_uuid = {
        "Sample Person Alice": uuid4(),
        "Sample Person Bob": uuid4(),
        "Sample Place": uuid4(),
        "Sample Organization": uuid4(),
        "Sample Project": uuid4(),
    }

    with pytest.raises(SeedError, match="Manual recovery needed"):
        await seed_relationships(rec, w, name_to_uuid, rels)


async def test_seed_relationships_optional_fields_propagate(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """notes, confidence, and active are all optional and pass through to
    the writer when present."""
    w, rec = writer_and_client
    rels = [
        {
            "from": "A",
            "to": "B",
            "relationship": "spouse",
            "notes": "ten years",
            "confidence": 0.95,
            "active": True,
        }
    ]
    name_to_uuid = {"A": uuid4(), "B": uuid4()}

    await seed_relationships(rec, w, name_to_uuid, rels)

    payload = rec.calls[0][1]
    assert payload["notes"] == "ten years"
    assert payload["confidence"] == 0.95
    assert payload["active"] is True


# ──────────────────────────────────────────────────────────────────────────────
# End-to-end — entities then relationships using the example fixtures
# ──────────────────────────────────────────────────────────────────────────────


async def test_end_to_end_seed_example_brain(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """The standard 2-step flow: seed entities, capture map, seed relationships
    using the captured map. Validates the full mechanism against the shipped
    example fixtures."""
    w, rec = writer_and_client

    name_to_uuid = await seed_entities(rec, w, load_entities_yaml(EXAMPLE_ENTITIES))
    assert len(name_to_uuid) == 5

    count = await seed_relationships(
        rec, w, name_to_uuid, load_relationships_yaml(EXAMPLE_RELATIONSHIPS)
    )
    assert count == 3

    # Confirm the writes hit the right tables in the right order
    entity_inserts = [c for c in rec.calls if c[0] == "helm_entities"]
    rel_inserts = [c for c in rec.calls if c[0] == "helm_entity_relationships"]
    assert len(entity_inserts) == 5
    assert len(rel_inserts) == 3
