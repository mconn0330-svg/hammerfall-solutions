"""Tests for T0.B7a — helm_entities deepening + helm_entity_relationships writers
+ read_entities helper.

Per the T0.B7 arch one-pager, each Tier 2 type gets its own test file with its
own fixtures so sub-PR test setups stay independent — when T0.B7b adds curiosities
and T0.B7c adds promises, neither shares state with this file.

Module-diff budget for T0.B7a (per arch note): ≤ ~150 lines added to memory module
proper, ≤ 50–80 line target. Migration files separate. Tests in this file are also
separate from the budget.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from memory.client import MemoryWriteFailed
from memory.outbox import Outbox
from memory.reader import read_entities
from memory.writer import MemoryWriter

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures — recording client (writer side) + recording select client (read side)
# ──────────────────────────────────────────────────────────────────────────────


class _RecordingClient:
    """In-memory MemoryClient stand-in. Captures every insert call's payload
    so tests assert what would have hit Supabase. Mirrors the recorder used
    in test_memory_writer.py — kept local so per-type test files stay
    self-contained."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((table, payload))
        return payload


class _FailingClient:
    """Always-fails MemoryClient stand-in. Used to exercise the outbox-fallback
    path in the new helpers."""

    async def insert(self, _table: str, _payload: dict[str, Any]) -> dict[str, Any]:
        raise MemoryWriteFailed("simulated transport failure", attempts=3)


class _RecordingSelectClient:
    """In-memory ReadClient stand-in for read_entities. Captures the params
    dict so tests assert the PostgREST query shape that would have been sent."""

    def __init__(self, return_rows: list[dict[str, Any]] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._return_rows = return_rows or []

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls.append((table, dict(params)))
        return list(self._return_rows)


@pytest.fixture
def writer() -> tuple[MemoryWriter, _RecordingClient]:
    rec = _RecordingClient()
    w = MemoryWriter(rec)  # type: ignore[arg-type]
    return w, rec


# ──────────────────────────────────────────────────────────────────────────────
# write_helm_entity_record — minimal + full + omit-none + table targeting
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_helm_entity_record_minimal_payload(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Minimum required fields: entity_type + name. All optional kwargs omitted —
    payload should contain ONLY the supplied keys (server applies defaults for
    aliases='{}', salience_decay=1.0, etc. via the migration)."""
    w, rec = writer
    await w.write_helm_entity_record(entity_type="person", name="Sarah Chen")

    table, payload = rec.calls[0]
    assert table == "helm_entities"
    assert payload == {"entity_type": "person", "name": "Sarah Chen"}


async def test_write_helm_entity_record_full_payload(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """All optional fields supplied — every key shows up in the payload."""
    w, rec = writer
    await w.write_helm_entity_record(
        entity_type="person",
        name="Sarah Chen",
        aliases=["Sarah", "Chen"],
        attributes={"employer": "Anthropic", "city": "SF"},
        summary="Friend who works at Anthropic.",
        salience_decay=0.9,
        embedding=[0.1, 0.2, 0.3],
    )

    table, payload = rec.calls[0]
    assert table == "helm_entities"
    assert payload["entity_type"] == "person"
    assert payload["name"] == "Sarah Chen"
    assert payload["aliases"] == ["Sarah", "Chen"]
    assert payload["attributes"] == {"employer": "Anthropic", "city": "SF"}
    assert payload["summary"] == "Friend who works at Anthropic."
    assert payload["salience_decay"] == 0.9
    assert payload["embedding"] == [0.1, 0.2, 0.3]


async def test_write_helm_entity_record_omits_none_fields(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """None-valued optional kwargs are omitted from payload so PostgREST
    applies the column default (e.g. salience_decay=1.0 from the migration)
    rather than persisting an explicit NULL."""
    w, rec = writer
    await w.write_helm_entity_record(
        entity_type="pet",
        name="Sanchez",
        aliases=None,
        attributes=None,
        summary=None,
        salience_decay=None,
        embedding=None,
    )

    _, payload = rec.calls[0]
    assert "aliases" not in payload
    assert "attributes" not in payload
    assert "summary" not in payload
    assert "salience_decay" not in payload
    assert "embedding" not in payload


async def test_write_helm_entity_record_routes_to_helm_entities_table(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Distinct from `write_entity()` (which routes to helm_memory) — this
    helper writes to helm_entities. Regression guard for any future refactor
    that confuses the two write paths."""
    w, rec = writer
    await w.write_helm_entity_record(entity_type="person", name="X")
    assert rec.calls[0][0] == "helm_entities"


async def test_write_helm_entity_record_pet_is_allowed(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """T0.B7a extends the spec's entity_type enum from 7 to 8 values to
    accommodate the production rows already seeded with entity_type='pet'.
    The Python helper has no client-side enum — server-side CHECK is
    authoritative — so this test just verifies the payload passes through
    cleanly. Server rejection (if 'pet' were dropped) would surface as
    MemoryWriteFailed at integration time."""
    w, rec = writer
    await w.write_helm_entity_record(entity_type="pet", name="Krieger")
    assert rec.calls[0][1]["entity_type"] == "pet"


# ──────────────────────────────────────────────────────────────────────────────
# write_helm_entity_relationship_record — minimal + full + UUID serialization
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_helm_entity_relationship_record_minimal_payload(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Minimum required fields: from_entity + to_entity + relationship.
    Defaults: active=True; notes/confidence omitted."""
    w, rec = writer
    from_id = uuid4()
    to_id = uuid4()
    await w.write_helm_entity_relationship_record(
        from_entity=from_id,
        to_entity=to_id,
        relationship="spouse",
    )

    table, payload = rec.calls[0]
    assert table == "helm_entity_relationships"
    assert payload["from_entity"] == str(from_id)
    assert payload["to_entity"] == str(to_id)
    assert payload["relationship"] == "spouse"
    assert payload["active"] is True
    assert "notes" not in payload
    assert "confidence" not in payload


async def test_write_helm_entity_relationship_record_full_payload(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Full payload — confidence is the spec-aligned name (was `strength`
    pre-T0.B7a). The migration renamed the column; this helper writes the
    new name."""
    w, rec = writer
    from_id = uuid4()
    to_id = uuid4()
    await w.write_helm_entity_relationship_record(
        from_entity=from_id,
        to_entity=to_id,
        relationship="parent",
        notes="biological",
        confidence=0.95,
        active=True,
    )

    _, payload = rec.calls[0]
    assert payload["notes"] == "biological"
    assert payload["confidence"] == 0.95
    # confidence (renamed from strength) is the new column name
    assert "strength" not in payload


async def test_write_helm_entity_relationship_record_accepts_uuid_or_string(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """UUID instances are stringified; raw strings pass through unchanged.
    Most callers will work with UUID objects from prior helm_entities writes,
    but the seed scripts pass pre-resolved string UUIDs."""
    w, rec = writer
    raw_string_id = "12345678-1234-1234-1234-123456789012"
    uuid_obj = UUID("87654321-4321-4321-4321-210987654321")

    await w.write_helm_entity_relationship_record(
        from_entity=raw_string_id,
        to_entity=uuid_obj,
        relationship="friend",
    )

    _, payload = rec.calls[0]
    assert payload["from_entity"] == raw_string_id
    assert payload["to_entity"] == str(uuid_obj)
    assert isinstance(payload["from_entity"], str)
    assert isinstance(payload["to_entity"], str)


async def test_write_helm_entity_relationship_record_active_false(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """active=False marks a retired relationship — kept in the table for
    audit trail per migration 004's design note."""
    w, rec = writer
    await w.write_helm_entity_relationship_record(
        from_entity=uuid4(),
        to_entity=uuid4(),
        relationship="spouse",
        active=False,
    )
    assert rec.calls[0][1]["active"] is False


# ──────────────────────────────────────────────────────────────────────────────
# Outbox fallback — both helpers honor the durable-on-failure contract
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_helm_entity_record_propagates_failure_without_outbox() -> None:
    """No outbox → transport failure surfaces as MemoryWriteFailed."""
    w = MemoryWriter(_FailingClient())  # type: ignore[arg-type]
    with pytest.raises(MemoryWriteFailed):
        await w.write_helm_entity_record(entity_type="person", name="X")


async def test_write_helm_entity_record_enqueues_on_failure_with_outbox(
    tmp_path: Any,
) -> None:
    """Outbox configured → transport failure routes payload to outbox; caller
    sees success. Mirrors the write_helm_frame_record outbox contract."""
    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        w = MemoryWriter(_FailingClient(), outbox=outbox)  # type: ignore[arg-type]
        payload = await w.write_helm_entity_record(entity_type="person", name="Sarah")

        assert payload["name"] == "Sarah"
        stats = await outbox.stats()
        assert stats.queued_count == 1
    finally:
        await outbox.aclose()


async def test_write_helm_entity_relationship_record_propagates_failure_without_outbox() -> None:
    """Same contract for the relationship writer."""
    w = MemoryWriter(_FailingClient())  # type: ignore[arg-type]
    with pytest.raises(MemoryWriteFailed):
        await w.write_helm_entity_relationship_record(
            from_entity=uuid4(),
            to_entity=uuid4(),
            relationship="spouse",
        )


async def test_write_helm_entity_relationship_record_enqueues_on_failure_with_outbox(
    tmp_path: Any,
) -> None:
    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        w = MemoryWriter(_FailingClient(), outbox=outbox)  # type: ignore[arg-type]
        await w.write_helm_entity_relationship_record(
            from_entity=uuid4(),
            to_entity=uuid4(),
            relationship="spouse",
        )
        stats = await outbox.stats()
        assert stats.queued_count == 1
    finally:
        await outbox.aclose()


# ──────────────────────────────────────────────────────────────────────────────
# read_entities — filter composition + default behavior
# ──────────────────────────────────────────────────────────────────────────────


async def test_read_entities_default_filters() -> None:
    """No kwargs → defaults: select=*, order=last_mentioned_at.desc, active=true.
    Used by the Memory widget's 'recently mentioned entities' query."""
    client = _RecordingSelectClient()
    await read_entities(client)

    table, params = client.calls[0]
    assert table == "helm_entities"
    assert params["select"] == "*"
    assert params["order"] == "last_mentioned_at.desc"
    assert params["active"] == "eq.true"
    # No type/name/alias/limit filters when not supplied
    assert "entity_type" not in params
    assert "name" not in params
    assert "aliases" not in params
    assert "limit" not in params


async def test_read_entities_by_entity_type_filter() -> None:
    """entity_type kwarg → adds eq.<value> filter. Validates the spec's
    `read_entities(type=...)` call shape."""
    client = _RecordingSelectClient()
    await read_entities(client, entity_type="person")
    assert client.calls[0][1]["entity_type"] == "eq.person"


async def test_read_entities_by_alias_uses_array_contains() -> None:
    """alias kwarg → `aliases=cs.{<alias>}` (PostgREST array-contains).
    The duplicate guard in Routine 4 calls this with the heard nickname."""
    client = _RecordingSelectClient()
    await read_entities(client, alias="Wes")
    assert client.calls[0][1]["aliases"] == "cs.{Wes}"


async def test_read_entities_by_name_exact_match() -> None:
    client = _RecordingSelectClient()
    await read_entities(client, name="Sarah Chen")
    assert client.calls[0][1]["name"] == "eq.Sarah Chen"


async def test_read_entities_active_only_can_be_disabled() -> None:
    """Default is active_only=True. Pass False to include retired entities
    (rare — usually for audit/inspection flows)."""
    client = _RecordingSelectClient()
    await read_entities(client, active_only=False)
    assert "active" not in client.calls[0][1]


async def test_read_entities_limit_propagates_as_string() -> None:
    """PostgREST takes limit as a string. The helper does the conversion so
    callers pass int."""
    client = _RecordingSelectClient()
    await read_entities(client, limit=10)
    assert client.calls[0][1]["limit"] == "10"


async def test_read_entities_returns_rows_unchanged() -> None:
    """The helper does no transformation — caller gets the raw rows from
    Supabase. Type filtering / shaping happens upstream of the wire."""
    rows = [
        {"id": "uuid1", "name": "Sarah", "entity_type": "person"},
        {"id": "uuid2", "name": "Krieger", "entity_type": "pet"},
    ]
    client = _RecordingSelectClient(return_rows=rows)
    result = await read_entities(client)
    assert result == rows


async def test_read_entities_filter_composition() -> None:
    """All filters AND together — caller can ask 'all active persons named
    Sarah' in one call."""
    client = _RecordingSelectClient()
    await read_entities(
        client,
        entity_type="person",
        name="Sarah Chen",
        alias="Sarah",
        limit=5,
    )
    params = client.calls[0][1]
    assert params["entity_type"] == "eq.person"
    assert params["name"] == "eq.Sarah Chen"
    assert params["aliases"] == "cs.{Sarah}"
    assert params["limit"] == "5"
    assert params["active"] == "eq.true"  # default still applies
