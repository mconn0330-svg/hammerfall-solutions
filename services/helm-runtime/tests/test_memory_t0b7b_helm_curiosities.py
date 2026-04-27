"""Tests for T0.B7b — helm_curiosities table writers + readers + status lifecycle.

Per-type test file (per arch one-pager point 6) — sub-PR test setups stay
independent. T0.B7c will mirror this shape with a third file when promises land.

Module-diff budget for T0.B7b (per arch note): ≤ ~150 lines added to memory
module proper, target 50–80. This file's tests are separate from the budget.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from memory.client import MemoryWriteFailed
from memory.outbox import Outbox
from memory.reader import read_curiosity, read_open_curiosities
from memory.writer import MemoryWriter, update_curiosity_status

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures — recording client (insert + select + patch) for end-to-end coverage
# ──────────────────────────────────────────────────────────────────────────────


class _RecordingClient:
    """Stand-in for MemoryClient (insert) AND ReadClient (select + patch).

    The seed mechanism + curiosity flow exercise multiple capabilities;
    keeping a single recorder per test file mirrors test_memory_seed.py.
    """

    def __init__(self, table_rows: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []  # (op, table, payload-or-filters)
        self.table_rows: dict[str, list[dict[str, Any]]] = table_rows or {}

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("insert", table, payload))
        persisted = {**payload, "id": payload.get("id", str(uuid4()))}
        self.table_rows.setdefault(table, []).append(persisted)
        return payload

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls.append(("select", table, dict(params)))
        rows = list(self.table_rows.get(table, []))
        # Honor the simple eq.<value> filters the curiosity readers use.
        for key, val in params.items():
            if key in ("select", "order", "limit"):
                continue
            if isinstance(val, str) and val.startswith("eq."):
                wanted = val[len("eq.") :]
                rows = [r for r in rows if str(r.get(key)) == wanted]
        return rows

    async def patch(
        self, table: str, filters: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        self.calls.append(("patch", table, {"filters": filters, "payload": payload}))
        # Apply the patch in-memory so subsequent selects see the new state.
        rows = self.table_rows.get(table, [])
        # Honor simple eq.<value> id filter
        id_filter = filters.get("id", "")
        wanted_id = id_filter[len("eq.") :] if id_filter.startswith("eq.") else id_filter
        for row in rows:
            if str(row.get("id")) == wanted_id:
                row.update(payload)
        return [payload]


class _FailingClient:
    """Always-fails MemoryClient stand-in for outbox-fallback path."""

    async def insert(self, _table: str, _payload: dict[str, Any]) -> dict[str, Any]:
        raise MemoryWriteFailed("simulated transport failure", attempts=3)


@pytest.fixture
def writer_and_client() -> tuple[MemoryWriter, _RecordingClient]:
    rec = _RecordingClient()
    w = MemoryWriter(rec)  # type: ignore[arg-type]
    return w, rec


# ──────────────────────────────────────────────────────────────────────────────
# write_helm_curiosity_record — payload shapes + table targeting
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_helm_curiosity_record_minimal_payload(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Minimum required fields: project + question. Defaults: agent='helm',
    status='open'. Optional fields omitted from payload."""
    w, rec = writer_and_client
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="What does Maxwell mean by 'Feats'?",
    )

    op, table, payload = rec.calls[0]
    assert op == "insert"
    assert table == "helm_curiosities"
    assert payload["project"] == "hammerfall-solutions"
    assert payload["question"] == "What does Maxwell mean by 'Feats'?"
    assert payload["agent"] == "helm"
    assert payload["status"] == "open"
    assert "formed_from" not in payload
    assert "priority" not in payload


async def test_write_helm_curiosity_record_full_payload(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """All optional fields supplied — formed_from + priority show up."""
    w, rec = writer_and_client
    source_memory_id = uuid4()
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="Why did Maxwell flip the recommendation twice?",
        formed_from=source_memory_id,
        priority="high",
    )

    _, _, payload = rec.calls[0]
    assert payload["formed_from"] == str(source_memory_id)
    assert payload["priority"] == "high"


async def test_write_helm_curiosity_record_routes_to_helm_curiosities_table(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Distinct from write_curiosity (which routes to helm_memory) — this
    helper writes to helm_curiosities. Regression guard mirroring the
    T0.B7a entity-record table-target test."""
    w, rec = writer_and_client
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="?",
    )
    assert rec.calls[0][1] == "helm_curiosities"


async def test_write_helm_curiosity_record_accepts_uuid_or_string_formed_from(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """formed_from accepts UUID instance or pre-stringified UUID — both
    serialize to string in the payload (PostgREST takes strings)."""
    w, rec = writer_and_client
    raw = "12345678-1234-1234-1234-123456789012"

    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="q1",
        formed_from=raw,
    )
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="q2",
        formed_from=uuid4(),
    )

    for call in rec.calls:
        _, _, payload = call
        assert isinstance(payload["formed_from"], str)


async def test_write_helm_curiosity_record_explicit_status_passes_through(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """status defaults to 'open' but caller can override (e.g., importing
    a pre-resolved curiosity from elsewhere)."""
    w, rec = writer_and_client
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="?",
        status="investigating",
    )
    assert rec.calls[0][2]["status"] == "investigating"


# ──────────────────────────────────────────────────────────────────────────────
# Outbox fallback — write_helm_curiosity_record honors the durability contract
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_helm_curiosity_record_propagates_failure_without_outbox() -> None:
    w = MemoryWriter(_FailingClient())  # type: ignore[arg-type]
    with pytest.raises(MemoryWriteFailed):
        await w.write_helm_curiosity_record(
            project="hammerfall-solutions",
            question="?",
        )


async def test_write_helm_curiosity_record_enqueues_on_failure_with_outbox(
    tmp_path: Any,
) -> None:
    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        w = MemoryWriter(_FailingClient(), outbox=outbox)  # type: ignore[arg-type]
        payload = await w.write_helm_curiosity_record(
            project="hammerfall-solutions",
            question="What is X?",
        )
        assert payload["question"] == "What is X?"
        stats = await outbox.stats()
        assert stats.queued_count == 1
    finally:
        await outbox.aclose()


# ──────────────────────────────────────────────────────────────────────────────
# write_curiosity (memory event in helm_memory) — distinct from canonical writer
# ──────────────────────────────────────────────────────────────────────────────


async def test_write_curiosity_routes_to_helm_memory_table(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """write_curiosity is the EVENT writer — goes to helm_memory with
    memory_type=curiosity. Mirrors the write_entity vs write_helm_entity_record
    pattern from T0.B7a."""
    w, rec = writer_and_client
    await w.write_curiosity(
        project="hammerfall-solutions",
        agent="helm",
        content="Formed curiosity: what is Feats?",
    )
    op, table, payload = rec.calls[0]
    assert op == "insert"
    assert table == "helm_memory"
    assert payload["memory_type"] == "curiosity"


# ──────────────────────────────────────────────────────────────────────────────
# read_open_curiosities + read_curiosity — filter shape + result shape
# ──────────────────────────────────────────────────────────────────────────────


async def test_read_open_curiosities_filter_shape() -> None:
    """Default filters: project=eq.<x>, agent=eq.helm, status=eq.open,
    order=formed_at.desc. Used by Prime context loader at session start."""
    rec = _RecordingClient()
    await read_open_curiosities(rec, project="hammerfall-solutions")

    op, table, params = rec.calls[0]
    assert op == "select"
    assert table == "helm_curiosities"
    assert params["project"] == "eq.hammerfall-solutions"
    assert params["agent"] == "eq.helm"
    assert params["status"] == "eq.open"
    assert params["order"] == "formed_at.desc"


async def test_read_open_curiosities_with_limit() -> None:
    """Prime context loader uses limit (top-N opens). PostgREST takes string."""
    rec = _RecordingClient()
    await read_open_curiosities(rec, project="hammerfall-solutions", limit=5)
    assert rec.calls[0][2]["limit"] == "5"


async def test_read_open_curiosities_excludes_non_open() -> None:
    """Pre-populate the recording client with curiosities in mixed states.
    Only 'open' should come back."""
    rec = _RecordingClient(
        table_rows={
            "helm_curiosities": [
                {
                    "id": str(uuid4()),
                    "project": "hammerfall-solutions",
                    "agent": "helm",
                    "question": "open one",
                    "status": "open",
                },
                {
                    "id": str(uuid4()),
                    "project": "hammerfall-solutions",
                    "agent": "helm",
                    "question": "investigating one",
                    "status": "investigating",
                },
                {
                    "id": str(uuid4()),
                    "project": "hammerfall-solutions",
                    "agent": "helm",
                    "question": "resolved one",
                    "status": "resolved",
                },
            ]
        }
    )
    rows = await read_open_curiosities(rec, project="hammerfall-solutions")
    assert len(rows) == 1
    assert rows[0]["status"] == "open"


async def test_read_curiosity_returns_row_when_found() -> None:
    target_id = str(uuid4())
    rec = _RecordingClient(
        table_rows={
            "helm_curiosities": [
                {"id": target_id, "question": "the one", "status": "open"},
                {"id": str(uuid4()), "question": "another", "status": "open"},
            ]
        }
    )
    row = await read_curiosity(rec, curiosity_id=target_id)
    assert row is not None
    assert row["question"] == "the one"


async def test_read_curiosity_returns_none_when_absent() -> None:
    rec = _RecordingClient()
    row = await read_curiosity(rec, curiosity_id=str(uuid4()))
    assert row is None


# ──────────────────────────────────────────────────────────────────────────────
# update_curiosity_status — lifecycle transitions + validation
# ──────────────────────────────────────────────────────────────────────────────


async def test_update_curiosity_status_to_investigating() -> None:
    """Simple transition open → investigating: only status changes, no
    resolved_at, no resolution."""
    rec = _RecordingClient()
    target_id = uuid4()

    await update_curiosity_status(
        rec,
        curiosity_id=target_id,
        new_status="investigating",
    )

    op, table, body = rec.calls[0]
    assert op == "patch"
    assert table == "helm_curiosities"
    assert body["filters"] == {"id": f"eq.{target_id}"}
    assert body["payload"]["status"] == "investigating"
    assert "resolved_at" not in body["payload"]
    assert "resolution" not in body["payload"]


async def test_update_curiosity_status_to_resolved_sets_resolved_at_and_resolution() -> None:
    """Resolved transition: resolved_at gets stamped, resolution text optional."""
    rec = _RecordingClient()
    await update_curiosity_status(
        rec,
        curiosity_id=uuid4(),
        new_status="resolved",
        resolution="Maxwell explained Feats are productized capabilities.",
    )

    payload = rec.calls[0][2]["payload"]
    assert payload["status"] == "resolved"
    assert "resolved_at" in payload
    assert payload["resolution"] == "Maxwell explained Feats are productized capabilities."


async def test_update_curiosity_status_to_resolved_without_resolution_text() -> None:
    """resolution is optional even on resolved — caller may not have text."""
    rec = _RecordingClient()
    await update_curiosity_status(
        rec,
        curiosity_id=uuid4(),
        new_status="resolved",
    )
    payload = rec.calls[0][2]["payload"]
    assert payload["status"] == "resolved"
    assert "resolved_at" in payload
    assert "resolution" not in payload


async def test_update_curiosity_status_to_abandoned_also_stamps_resolved_at() -> None:
    """Abandoned curiosities get resolved_at too — the moment they were
    set aside (audit trail)."""
    rec = _RecordingClient()
    await update_curiosity_status(
        rec,
        curiosity_id=uuid4(),
        new_status="abandoned",
        resolution="Out of scope; superseded by T1 launch focus.",
    )
    payload = rec.calls[0][2]["payload"]
    assert payload["status"] == "abandoned"
    assert "resolved_at" in payload


async def test_update_curiosity_status_rejects_invalid_status() -> None:
    """Client-side validation against the same enum the schema CHECK
    enforces — fail-fast with ValueError, not a Postgres error."""
    rec = _RecordingClient()
    with pytest.raises(ValueError, match="must be one of"):
        await update_curiosity_status(
            rec,
            curiosity_id=uuid4(),
            new_status="bogus_status",
        )
    # No PATCH should have been sent on validation failure
    assert not rec.calls


# ──────────────────────────────────────────────────────────────────────────────
# End-to-end lifecycle — form → list → resolve → drops out
# ──────────────────────────────────────────────────────────────────────────────


async def test_lifecycle_form_list_resolve_drops_out(
    writer_and_client: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Standard lifecycle round-trip:
    1. Form a curiosity (canonical row write)
    2. read_open_curiosities returns it
    3. update_curiosity_status(resolved)
    4. read_open_curiosities no longer returns it (status filter)
    """
    w, rec = writer_and_client

    # 1. Form
    await w.write_helm_curiosity_record(
        project="hammerfall-solutions",
        question="What did Maxwell mean by 'Feats'?",
    )

    # 2. List opens — should include the new one
    opens_before = await read_open_curiosities(rec, project="hammerfall-solutions")
    assert len(opens_before) == 1
    new_id = opens_before[0]["id"]

    # 3. Resolve
    await update_curiosity_status(
        rec,
        curiosity_id=new_id,
        new_status="resolved",
        resolution="Productized capability bundles.",
    )

    # 4. List opens — should no longer include it (status flipped to resolved)
    opens_after = await read_open_curiosities(rec, project="hammerfall-solutions")
    assert len(opens_after) == 0
