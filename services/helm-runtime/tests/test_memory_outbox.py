"""Tests for memory.outbox — durable enqueue + drain + dead-letter."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from memory.outbox import DrainResult, Outbox, OutboxStats, stop_drain_loop

# ─── Fixtures + helpers ─────────────────────────────────────────────────────


@pytest.fixture
async def outbox(tmp_path: Path) -> AsyncGenerator[Outbox, None]:
    """Fresh Outbox in a tmp dir per test."""
    o = Outbox(tmp_path / "outbox.db")
    await o.connect()
    yield o
    await o.aclose()


class _RecordingClient:
    """In-memory _InsertCapable. Records every insert; configurable to fail."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_with: Exception | None = None

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((table, payload))
        if self.fail_with is not None:
            raise self.fail_with
        return payload


# ─── Connection lifecycle ──────────────────────────────────────────────────


async def test_connect_creates_parent_dirs(tmp_path: Path) -> None:
    """Outbox path can include directories that don't exist yet — connect()
    creates them."""
    nested = tmp_path / "subdir" / "deeper" / "outbox.db"
    o = Outbox(nested)
    await o.connect()
    assert nested.exists()
    assert nested.parent.is_dir()
    await o.aclose()


async def test_connect_is_idempotent(tmp_path: Path) -> None:
    o = Outbox(tmp_path / "outbox.db")
    await o.connect()
    await o.connect()  # second call is a no-op
    await o.aclose()


async def test_aclose_is_idempotent(tmp_path: Path) -> None:
    o = Outbox(tmp_path / "outbox.db")
    await o.connect()
    await o.aclose()
    await o.aclose()  # second call is a no-op


async def test_use_before_connect_raises(tmp_path: Path) -> None:
    o = Outbox(tmp_path / "outbox.db")
    with pytest.raises(RuntimeError, match="connect"):
        await o.enqueue("helm_memory", {"x": 1})


async def test_invalid_max_attempts_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Outbox(tmp_path / "outbox.db", max_attempts=0)


# ─── Enqueue ───────────────────────────────────────────────────────────────


async def test_enqueue_returns_row_id(outbox: Outbox) -> None:
    row_id = await outbox.enqueue("helm_memory", {"content": "x"})
    assert isinstance(row_id, int)
    assert row_id >= 1


async def test_enqueue_increments_id_per_call(outbox: Outbox) -> None:
    a = await outbox.enqueue("helm_memory", {"content": "a"})
    b = await outbox.enqueue("helm_memory", {"content": "b"})
    assert b > a


async def test_enqueue_serializes_payload_as_json(outbox: Outbox) -> None:
    """Roundtrip through enqueue → drain confirms JSON serialization."""
    payload = {"nested": {"list": [1, 2, 3], "key": "value"}}
    await outbox.enqueue("helm_memory", payload)

    client = _RecordingClient()
    await outbox.drain(client)

    assert len(client.calls) == 1
    assert client.calls[0] == ("helm_memory", payload)


async def test_concurrent_enqueue_produces_distinct_ids(outbox: Outbox) -> None:
    """100 concurrent enqueues — all 100 rows present, all unique ids."""
    payloads = [{"content": f"entry-{i}"} for i in range(100)]
    ids = await asyncio.gather(*(outbox.enqueue("helm_memory", p) for p in payloads))
    assert len(set(ids)) == 100
    s = await outbox.stats()
    assert s.queued_count == 100


# ─── Drain — happy path ─────────────────────────────────────────────────────


async def test_drain_empty_returns_zeros(outbox: Outbox) -> None:
    client = _RecordingClient()
    result = await outbox.drain(client)
    assert result == DrainResult(drained=0, failed=0, dead_lettered=0)


async def test_drain_one_succeeds(outbox: Outbox) -> None:
    await outbox.enqueue("helm_memory", {"content": "x"})
    client = _RecordingClient()
    result = await outbox.drain(client)
    assert result == DrainResult(drained=1, failed=0, dead_lettered=0)
    s = await outbox.stats()
    assert s.queued_count == 0


async def test_drain_processes_in_id_order(outbox: Outbox) -> None:
    """Oldest entries flush first — order is preserved."""
    for i in range(5):
        await outbox.enqueue("helm_memory", {"order": i})
    client = _RecordingClient()
    await outbox.drain(client)
    assert [c[1]["order"] for c in client.calls] == [0, 1, 2, 3, 4]


async def test_drain_respects_batch_size(outbox: Outbox) -> None:
    for i in range(10):
        await outbox.enqueue("helm_memory", {"i": i})
    client = _RecordingClient()
    result = await outbox.drain(client, batch_size=3)
    assert result.drained == 3
    s = await outbox.stats()
    assert s.queued_count == 7


# ─── Drain — failure + retry ────────────────────────────────────────────────


async def test_drain_increments_attempt_count_on_failure(outbox: Outbox) -> None:
    await outbox.enqueue("helm_memory", {"content": "x"})
    client = _RecordingClient()
    client.fail_with = RuntimeError("supabase down")

    result = await outbox.drain(client)
    assert result == DrainResult(drained=0, failed=1, dead_lettered=0)

    # Entry should still be in the queue (will retry next pass)
    s = await outbox.stats()
    assert s.queued_count == 1


async def test_drain_recovers_after_transient_failure(outbox: Outbox) -> None:
    await outbox.enqueue("helm_memory", {"content": "x"})
    client = _RecordingClient()
    client.fail_with = RuntimeError("transient")

    # First pass fails
    await outbox.drain(client)
    s = await outbox.stats()
    assert s.queued_count == 1

    # Recovery
    client.fail_with = None
    result = await outbox.drain(client)
    assert result.drained == 1
    s = await outbox.stats()
    assert s.queued_count == 0


async def test_drain_dead_letters_after_max_attempts(tmp_path: Path) -> None:
    """After max_attempts failures, the entry moves to outbox_dead_letter."""
    o = Outbox(tmp_path / "outbox.db", max_attempts=3)
    await o.connect()
    try:
        await o.enqueue("helm_memory", {"content": "doomed"})

        client = _RecordingClient()
        client.fail_with = RuntimeError("persistent failure")

        # Three drain passes — fail / fail / dead-letter
        for expected_state in [(0, 1, 0), (0, 1, 0), (0, 0, 1)]:
            result = await o.drain(client)
            assert (result.drained, result.failed, result.dead_lettered) == expected_state

        s = await o.stats()
        assert s.queued_count == 0
        assert s.dead_letter_count == 1
    finally:
        await o.aclose()


async def test_dead_letter_row_preserves_payload_and_original_id(tmp_path: Path) -> None:
    """The dead-letter table keeps everything needed for replay."""
    o = Outbox(tmp_path / "outbox.db", max_attempts=1)
    await o.connect()
    try:
        original_id = await o.enqueue("helm_memory", {"content": "doomed", "x": 42})
        client = _RecordingClient()
        client.fail_with = RuntimeError("nope")
        await o.drain(client)

        # Read directly from the dead-letter table to confirm shape
        db = o._require_connection()
        async with db.execute(
            "SELECT original_id, table_name, payload, attempt_count, last_error "
            "FROM outbox_dead_letter"
        ) as cursor:
            rows = list(await cursor.fetchall())
        assert len(rows) == 1
        row = rows[0]
        assert int(row[0]) == original_id
        assert row[1] == "helm_memory"
        # Payload preserved
        import json as _json

        assert _json.loads(row[2]) == {"content": "doomed", "x": 42}
        assert int(row[3]) == 1
        assert "nope" in str(row[4])
    finally:
        await o.aclose()


# ─── Stats / session_start_context ─────────────────────────────────────────


async def test_stats_empty(outbox: Outbox) -> None:
    s = await outbox.stats()
    assert s == OutboxStats(queued_count=0, dead_letter_count=0, oldest_queued_at=None)


async def test_stats_reports_queued_and_oldest(outbox: Outbox) -> None:
    await outbox.enqueue("helm_memory", {"content": "first"})
    await outbox.enqueue("helm_memory", {"content": "second"})
    s = await outbox.stats()
    assert s.queued_count == 2
    assert s.dead_letter_count == 0
    assert s.oldest_queued_at is not None
    assert "T" in s.oldest_queued_at  # ISO-8601


async def test_session_start_context_dict_shape(outbox: Outbox) -> None:
    """V2 spec requires this exact shape so Routine 0 can read it."""
    await outbox.enqueue("helm_memory", {"content": "queued"})
    ctx = await outbox.session_start_context()
    assert set(ctx.keys()) == {
        "queued_count",
        "dead_letter_count",
        "oldest_queued_at",
    }
    assert ctx["queued_count"] == 1
    assert ctx["dead_letter_count"] == 0
    assert ctx["oldest_queued_at"] is not None


async def test_session_start_context_surfaces_queue_state(outbox: Outbox) -> None:
    """Per V2 spec test_session_start_context_surfaces_queue_state — the
    helper returns non-zero queued_count when outbox has pending writes."""
    ctx = await outbox.session_start_context()
    assert ctx["queued_count"] == 0  # baseline
    await outbox.enqueue("helm_memory", {"content": "x"})
    ctx = await outbox.session_start_context()
    assert ctx["queued_count"] == 1


# ─── drain_loop ────────────────────────────────────────────────────────────


async def test_drain_loop_drains_pending_entries(outbox: Outbox) -> None:
    """Background loop picks up entries enqueued before it started."""
    for i in range(3):
        await outbox.enqueue("helm_memory", {"i": i})

    client = _RecordingClient()
    task = asyncio.create_task(outbox.drain_loop(client, interval=0.05))
    # Give the loop a couple iterations
    await asyncio.sleep(0.2)
    await stop_drain_loop(task)

    assert len(client.calls) == 3
    s = await outbox.stats()
    assert s.queued_count == 0


async def test_drain_loop_picks_up_new_entries_during_run(outbox: Outbox) -> None:
    """Entry enqueued AFTER loop starts still gets drained."""
    client = _RecordingClient()
    task = asyncio.create_task(outbox.drain_loop(client, interval=0.05))
    await asyncio.sleep(0.05)
    await outbox.enqueue("helm_memory", {"late": True})
    await asyncio.sleep(0.2)
    await stop_drain_loop(task)

    assert any(c[1].get("late") is True for c in client.calls)


async def test_drain_loop_survives_iteration_exception(outbox: Outbox) -> None:
    """One bad iteration must not kill the worker — loop catches and continues."""
    await outbox.enqueue("helm_memory", {"i": 1})
    client = _RecordingClient()
    client.fail_with = RuntimeError("transient")

    task = asyncio.create_task(outbox.drain_loop(client, interval=0.05))
    await asyncio.sleep(0.15)  # at least 2 iterations
    # Now recover
    client.fail_with = None
    await asyncio.sleep(0.15)
    await stop_drain_loop(task)

    s = await outbox.stats()
    assert s.queued_count == 0  # eventually drained


async def test_stop_drain_loop_helper_cleanly_cancels(outbox: Outbox) -> None:
    """stop_drain_loop helper cancels + awaits without raising."""
    client = _RecordingClient()
    task = asyncio.create_task(outbox.drain_loop(client, interval=10.0))
    await asyncio.sleep(0.05)
    # Should return cleanly
    await stop_drain_loop(task)
    assert task.done()
    assert task.cancelled()


# ─── Crash durability ──────────────────────────────────────────────────────


async def test_entries_survive_reopen(tmp_path: Path) -> None:
    """Process death between enqueue and drain doesn't lose data — open a
    second Outbox on the same file and find what was queued."""
    db_path = tmp_path / "outbox.db"

    o1 = Outbox(db_path)
    await o1.connect()
    await o1.enqueue("helm_memory", {"content": "persisted"})
    await o1.aclose()

    # Simulate process restart
    o2 = Outbox(db_path)
    await o2.connect()
    try:
        s = await o2.stats()
        assert s.queued_count == 1

        client = _RecordingClient()
        result = await o2.drain(client)
        assert result.drained == 1
        assert client.calls[0] == ("helm_memory", {"content": "persisted"})
    finally:
        await o2.aclose()
