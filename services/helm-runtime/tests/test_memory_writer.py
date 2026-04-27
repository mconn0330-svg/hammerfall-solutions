"""Tests for memory.writer — generic write() + type-specific helpers."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from memory.client import MemoryClient
from memory.models import MemoryEntry, MemoryType
from memory.settings import MemorySettings
from memory.writer import MemoryWriter


class _RecordingClient:
    """In-memory MemoryClient stand-in. Captures every insert call's payload
    so tests assert what would have hit Supabase."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((table, payload))
        return payload


@pytest.fixture
def writer() -> tuple[MemoryWriter, _RecordingClient]:
    rec = _RecordingClient()
    w = MemoryWriter(rec)  # type: ignore[arg-type]
    return w, rec


# ─── Generic write() ────────────────────────────────────────────────────────


async def test_write_routes_to_helm_memory_table(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write(
        project="hammerfall-solutions",
        agent="helm",
        memory_type=MemoryType.SCRATCHPAD,
        content="HEARTBEAT — ok",
    )
    assert len(rec.calls) == 1
    table, payload = rec.calls[0]
    assert table == "helm_memory"
    assert payload["memory_type"] == "scratchpad"
    assert payload["content"] == "HEARTBEAT — ok"


async def test_write_returns_constructed_entry(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """The writer returns the locally-constructed entry — id/timestamps
    are client-generated so callers can reference them before Supabase
    confirms the insert."""
    w, rec = writer
    entry = await w.write(
        project="p",
        agent="helm",
        memory_type=MemoryType.BEHAVIORAL,
        content="x",
    )
    assert isinstance(entry, MemoryEntry)
    assert entry.memory_type is MemoryType.BEHAVIORAL
    # Returned entry's id matches what landed in the payload
    assert str(entry.id) == rec.calls[0][1]["id"]


async def test_write_accepts_string_memory_type(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Callers can pass either the enum or its string — saves an import."""
    w, rec = writer
    await w.write(
        project="p",
        agent="helm",
        memory_type="behavioral",
        content="x",
    )
    assert rec.calls[0][1]["memory_type"] == "behavioral"


async def test_write_rejects_unknown_memory_type_string(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, _ = writer
    with pytest.raises(ValueError):
        await w.write(
            project="p",
            agent="helm",
            memory_type="not_a_real_type",
            content="x",
        )


async def test_write_propagates_optional_fields(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    subj = uuid4()
    await w.write(
        project="p",
        agent="helm",
        memory_type=MemoryType.OBSERVATION,
        content="x",
        confidence=0.9,
        full_content={"k": "v"},
        sync_ready=True,
        embedding=[0.0] * 1536,
        subject_ref=subj,
    )
    payload = rec.calls[0][1]
    assert payload["confidence"] == 0.9
    assert payload["full_content"] == {"k": "v"}
    assert payload["sync_ready"] is True
    assert payload["subject_ref"] == str(subj)
    assert len(payload["embedding"]) == 1536


# ─── Type-specific helpers ──────────────────────────────────────────────────


async def test_write_frame_sets_correct_type_and_full_content(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_frame(
        project="p",
        agent="helm",
        content="Frame summary",
        full_content={"frame": {"turn": 5, "stakes": "high"}},
    )
    payload = rec.calls[0][1]
    assert payload["memory_type"] == "frame"
    assert payload["full_content"]["frame"]["turn"] == 5


async def test_write_behavioral_with_sync_ready(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_behavioral(
        project="p",
        agent="helm",
        content="[SYNC-READY] T0.B1 shipped",
        sync_ready=True,
    )
    payload = rec.calls[0][1]
    assert payload["memory_type"] == "behavioral"
    assert payload["sync_ready"] is True


async def test_write_correction_routes_to_correction_type(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_correction(
        project="p",
        agent="helm",
        content="[CORRECTION] — Missed: X — Correct: Y — Count: 1",
    )
    assert rec.calls[0][1]["memory_type"] == "correction"


# ─── Em-dash normalization (T0.B6) ──────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected_prefix",
    [
        ("Pattern -- some-slug | thing | domain: x", "Pattern — "),
        ("Pattern - some-slug | thing | domain: x", "Pattern — "),
        ("Pattern—some-slug | thing | domain: x", "Pattern — "),
        ("Pattern – some-slug | thing | domain: x", "Pattern — "),  # en-dash
        ("Pattern — some-slug | thing | domain: x", "Pattern — "),  # already canonical
    ],
)
async def test_write_normalizes_pattern_prefix_to_canonical_em_dash(
    writer: tuple[MemoryWriter, _RecordingClient],
    raw: str,
    expected_prefix: str,
) -> None:
    """Pattern detection downstream uses U+2014 EM DASH. Variants typed by
    callers (--, -, no-space, en-dash) must normalize to the canonical
    `Pattern — ` so the dual-write hook + graduation count never miss a
    real pattern entry."""
    w, rec = writer
    await w.write(
        project="p",
        agent="helm",
        memory_type=MemoryType.PATTERN,
        content=raw,
    )
    written = rec.calls[0][1]["content"]
    assert written.startswith(expected_prefix)


async def test_write_does_not_normalize_non_pattern_content(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Behavioral / scratchpad / etc. content with leading dashes is
    passed through unchanged — only the literal Pattern prefix triggers."""
    w, rec = writer
    await w.write(
        project="p",
        agent="helm",
        memory_type=MemoryType.BEHAVIORAL,
        content="Decision -- ship the thing",
    )
    assert rec.calls[0][1]["content"] == "Decision -- ship the thing"


async def test_write_pattern_constructs_canonical_content(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Pattern entries have a strict format the graduation rule depends on:
    `Pattern — slug | statement | domain: X`"""
    w, rec = writer
    await w.write_pattern(
        project="p",
        agent="helm",
        slug="small-prs-strict-merge-order",
        statement="Maxwell prefers small single-purpose PRs",
        domain="process",
    )
    content = rec.calls[0][1]["content"]
    assert content == (
        "Pattern — small-prs-strict-merge-order | "
        "Maxwell prefers small single-purpose PRs | domain: process"
    )


async def test_write_pattern_normalizes_slug(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Defensive slugification — caller passes loose string, we normalize."""
    w, rec = writer
    await w.write_pattern(
        project="p",
        agent="helm",
        slug="Small PRs Strict Merge Order",
        statement="x",
        domain="process",
    )
    content = rec.calls[0][1]["content"]
    assert "small-prs-strict-merge-order" in content


async def test_write_pattern_appends_scope_when_system(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_pattern(
        project="p",
        agent="helm",
        slug="never-amend-published-commits",
        statement="Always create new commits, not amends",
        domain="git",
        scope="system",
    )
    content = rec.calls[0][1]["content"]
    assert content.endswith("| scope: system")


async def test_write_pattern_omits_scope_when_user(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Default scope is user — content does NOT include the scope tag
    (existing pattern entries don't either; consistency matters for the
    ILIKE prefix-match graduation count)."""
    w, rec = writer
    await w.write_pattern(
        project="p",
        agent="helm",
        slug="x",
        statement="y",
        domain="d",
    )
    assert "scope:" not in rec.calls[0][1]["content"]


async def test_write_pattern_rejects_empty_slug(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, _ = writer
    with pytest.raises(ValueError, match="resolves to empty"):
        await w.write_pattern(
            project="p",
            agent="helm",
            slug="!!!",  # slugifies to empty
            statement="x",
            domain="d",
        )


async def test_write_monologue_includes_embedding(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    """Monologue is a high-value retrieval target — embeddings matter."""
    w, rec = writer
    await w.write_monologue(
        project="p",
        agent="helm",
        content="I've been thinking about...",
        embedding=[0.1] * 1536,
    )
    payload = rec.calls[0][1]
    assert payload["memory_type"] == "monologue"
    assert len(payload["embedding"]) == 1536


async def test_write_observation_with_confidence(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_observation(
        project="p",
        agent="helm",
        content="Maxwell consistently prefers BLUF",
        confidence=0.85,
    )
    payload = rec.calls[0][1]
    assert payload["memory_type"] == "observation"
    assert payload["confidence"] == 0.85


async def test_write_belief_update(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_belief_update(
        project="p",
        agent="helm",
        content="belief 'small-prs' graduated +0.05",
    )
    assert rec.calls[0][1]["memory_type"] == "belief_update"


async def test_write_entity_with_subject_ref(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    subj = uuid4()
    await w.write_entity(
        project="p",
        agent="helm",
        content="[NEW-ENTITY] — person: Sarah",
        subject_ref=subj,
    )
    payload = rec.calls[0][1]
    assert payload["memory_type"] == "entity"
    assert payload["subject_ref"] == str(subj)


async def test_write_relationship(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_relationship(
        project="p",
        agent="helm",
        content="Maxwell works at Hammerfall Solutions",
    )
    assert rec.calls[0][1]["memory_type"] == "relationship"


async def test_write_decision(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_decision(
        project="p",
        agent="helm",
        content="Decision: separate runtime for demo sandbox",
    )
    assert rec.calls[0][1]["memory_type"] == "decision"


async def test_write_scratchpad_minimal(
    writer: tuple[MemoryWriter, _RecordingClient],
) -> None:
    w, rec = writer
    await w.write_scratchpad(
        project="p",
        agent="helm",
        content="HEARTBEAT — building T0.B1",
    )
    assert rec.calls[0][1]["memory_type"] == "scratchpad"


# ─── Integration: writer + real MemoryClient (mocked transport) ─────────────


async def test_writer_through_real_client_with_mock_transport() -> None:
    """End-to-end through MemoryClient with httpx MockTransport — confirms
    payload shape lands in Supabase POST as expected."""
    import httpx

    captured: list[tuple[str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, json=[{"id": "supabase-id"}], request=request)

    settings = MemorySettings(
        supabase_url="https://test.supabase.co",
        supabase_service_key="k",
        retry_backoff_base=0.0,
        retry_backoff_max=0.0,
    )
    client = MemoryClient(settings)
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    w = MemoryWriter(client)

    await w.write_behavioral(
        project="hammerfall-solutions",
        agent="helm",
        content="Decision: T0.B1 shipped",
    )

    assert len(captured) == 1
    url, body = captured[0]
    assert url == "https://test.supabase.co/rest/v1/helm_memory"
    assert body["memory_type"] == "behavioral"
    assert body["content"] == "Decision: T0.B1 shipped"
    assert "id" in body
    assert "created_at" in body
    assert "session_date" in body

    await client.aclose()


# ─── Outbox integration (T0.B2) ─────────────────────────────────────────────


class _FailingClient:
    """Client that always raises MemoryWriteFailed on insert."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        from memory.client import MemoryWriteFailed

        self.calls.append((table, payload))
        raise MemoryWriteFailed("simulated transport failure", attempts=3)


class _CircuitOpenClient:
    """Client that always raises CircuitBreakerOpen on insert."""

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        from memory.circuit_breaker import CircuitBreakerOpen

        raise CircuitBreakerOpen("simulated open circuit")


async def test_writer_propagates_failure_when_no_outbox() -> None:
    """Without outbox, transport failures bubble up as before — preserves
    the T0.B1 behavior so callers can opt out of the durable backstop."""
    from memory.client import MemoryWriteFailed

    w = MemoryWriter(_FailingClient())  # type: ignore[arg-type]
    with pytest.raises(MemoryWriteFailed):
        await w.write(
            project="p",
            agent="helm",
            memory_type=MemoryType.SCRATCHPAD,
            content="x",
        )


async def test_writer_enqueues_to_outbox_on_transport_failure(tmp_path: Any) -> None:
    """With outbox configured, MemoryWriteFailed → enqueue → caller sees
    a normal MemoryEntry return."""
    from memory.outbox import Outbox

    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        client = _FailingClient()
        w = MemoryWriter(client, outbox=outbox)  # type: ignore[arg-type]

        entry = await w.write(
            project="hammerfall-solutions",
            agent="helm",
            memory_type=MemoryType.BEHAVIORAL,
            content="Decision: route through outbox on failure",
        )

        # Caller sees a normal entry — write was "accepted"
        assert isinstance(entry, MemoryEntry)
        # But it landed in the outbox, not Supabase
        stats = await outbox.stats()
        assert stats.queued_count == 1
        assert stats.dead_letter_count == 0
    finally:
        await outbox.aclose()


async def test_writer_enqueues_to_outbox_when_circuit_open(tmp_path: Any) -> None:
    """CircuitBreakerOpen also routes to outbox — fail-fast on the client
    side becomes durable on the caller side."""
    from memory.outbox import Outbox

    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        w = MemoryWriter(_CircuitOpenClient(), outbox=outbox)  # type: ignore[arg-type]
        entry = await w.write(
            project="p",
            agent="helm",
            memory_type=MemoryType.SCRATCHPAD,
            content="x",
        )
        assert isinstance(entry, MemoryEntry)
        s = await outbox.stats()
        assert s.queued_count == 1
    finally:
        await outbox.aclose()


async def test_writer_outbox_payload_round_trips_through_drain(tmp_path: Any) -> None:
    """Enqueued payload deserializes correctly when the drain loop sends
    it later — the JSON round-trip preserves the entry shape."""
    from memory.outbox import Outbox

    outbox = Outbox(tmp_path / "outbox.db")
    await outbox.connect()
    try:
        # First write fails → enqueued
        w_failing = MemoryWriter(_FailingClient(), outbox=outbox)  # type: ignore[arg-type]
        entry = await w_failing.write(
            project="hammerfall-solutions",
            agent="helm",
            memory_type=MemoryType.BEHAVIORAL,
            content="Decision: enqueue then drain",
            full_content={"key": "value"},
        )

        # Now drain via a healthy client — confirm payload survives
        recorder = _RecordingClient()
        result = await outbox.drain(recorder)
        assert result.drained == 1
        assert len(recorder.calls) == 1
        table, payload = recorder.calls[0]
        assert table == "helm_memory"
        assert payload["id"] == str(entry.id)
        assert payload["content"] == "Decision: enqueue then drain"
        assert payload["full_content"] == {"key": "value"}
        assert payload["memory_type"] == "behavioral"
    finally:
        await outbox.aclose()
