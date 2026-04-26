"""Smoke tests for archivist agent — verifies migration to MemoryWriter +
read_frames helper.

Two code paths covered:
  1. Cold-frame migration — reads via memory.read_frames, writes via
     writer.write_frame (memory_type=FRAME), deletes the helm_frames row.
  2. Contemplator write handoff — writes pattern entries, curiosity flags,
     and reflection through writer; belief/personality PATCHes still through
     supabase (sibling-table modify, not in T0.B3 migration scope).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import archivist as archivist_agent
from middleware import InvokeRequest


def _summary_response(text: str) -> MagicMock:
    """Build a model-response mock with the given text in choices[0].message.content."""
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = text
    return r


# ─── Cold-frame migration path ──────────────────────────────────────────────


@pytest.fixture
def cold_frame_row() -> dict[str, Any]:
    return {
        "id": "frame-uuid-1",
        "layer": "cold",
        "frame_status": "canonical",
        "frame_json": {
            "turn": 3,
            "timestamp": "2026-04-22T14:30:00Z",
            "session_id": "old-session",
            "user": "User said something",
            "helm": "Helm replied something",
            "topic": "test topic",
            "domain": "process",
            "entities_mentioned": [],
            "belief_links": [],
            "frame_status": "canonical",
        },
    }


@pytest.fixture
def mock_router_for_summary() -> MagicMock:
    router = MagicMock()
    router.invoke = AsyncMock(return_value=_summary_response("Test summary of the turn."))
    return router


@pytest.fixture
def mock_writer() -> MagicMock:
    w = MagicMock()
    w.write_frame = AsyncMock(return_value=None)
    w.write_monologue = AsyncMock(return_value=None)
    w.write = AsyncMock(return_value=None)
    return w


@pytest.fixture
def request_obj() -> InvokeRequest:
    return InvokeRequest(
        session_id="archivist-test-session",
        turn_number=0,
        user_message="",
        helm_response="",
        context={"project": "hammerfall-solutions", "agent": "helm"},
    )


async def test_archivist_writes_frame_through_writer_not_supabase_insert(
    request_obj: InvokeRequest,
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
    cold_frame_row: dict[str, Any],
) -> None:
    """The migration target: Archivist's frame migration writes to helm_memory
    via writer.write_frame, not supabase.insert."""
    sb = MagicMock()
    # First call: read_frames(layer='cold') → returns one cold frame
    sb.select = AsyncMock(return_value=[cold_frame_row])
    sb.delete = AsyncMock(return_value=None)
    sb.insert = AsyncMock(return_value={})  # should NEVER be called

    await archivist_agent.handle(request_obj, mock_router_for_summary, sb, mock_writer)

    # Frame written through MemoryWriter
    assert mock_writer.write_frame.await_count == 1
    call_kwargs = mock_writer.write_frame.await_args.kwargs
    assert call_kwargs["project"] == "hammerfall-solutions"
    assert call_kwargs["agent"] == "helm"
    assert call_kwargs["content"] == "Test summary of the turn."
    assert call_kwargs["full_content"]["topic"] == "test topic"
    # Frame status from the column is authoritative — gets injected into full_content
    assert call_kwargs["full_content"]["frame_status"] == "canonical"
    # session_date preserved from the frame's original timestamp (not today)
    from datetime import date

    assert call_kwargs["session_date"] == date(2026, 4, 22)

    # NOT through supabase.insert
    assert sb.insert.await_count == 0
    # helm_frames row deleted after successful write
    assert sb.delete.await_count == 1
    sb.delete.assert_awaited_with("helm_frames", {"id": "frame-uuid-1"})


async def test_archivist_uses_read_frames_for_cold_queue(
    request_obj: InvokeRequest,
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
) -> None:
    """The cold-frame read goes through memory.read_frames (centralized
    helper) rather than ad-hoc supabase.select calls."""
    sb = MagicMock()
    sb.select = AsyncMock(return_value=[])  # empty — no migration
    sb.delete = AsyncMock(return_value=None)

    await archivist_agent.handle(request_obj, mock_router_for_summary, sb, mock_writer)

    # read_frames invoked on supabase with the helm_frames table + cold filter
    assert sb.select.await_count >= 1
    table_arg, params_arg = sb.select.await_args.args
    assert table_arg == "helm_frames"
    assert params_arg["layer"] == "eq.cold"


async def test_archivist_leaves_frame_in_cold_on_writer_failure(
    request_obj: InvokeRequest,
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
    cold_frame_row: dict[str, Any],
) -> None:
    """If writer.write_frame raises, the helm_frames row is NOT deleted —
    frame stays in cold for retry next invocation."""
    sb = MagicMock()
    sb.select = AsyncMock(return_value=[cold_frame_row])
    sb.delete = AsyncMock(return_value=None)

    mock_writer.write_frame = AsyncMock(side_effect=RuntimeError("supabase down"))

    result = await archivist_agent.handle(request_obj, mock_router_for_summary, sb, mock_writer)

    # write attempted
    assert mock_writer.write_frame.await_count == 1
    # delete NOT called — frame stays in cold
    assert sb.delete.await_count == 0
    # Result reports the failure
    assert "1 failed" in result


# ─── Contemplator handoff path ──────────────────────────────────────────────


async def test_archivist_contemplator_handoff_writes_pattern_through_writer(
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
) -> None:
    """Pattern entries from Contemplator handoff route through writer.write
    with memory_type=PATTERN, NOT supabase.insert."""
    sb = MagicMock()
    sb.insert = AsyncMock(return_value={})  # should NEVER be called

    req = InvokeRequest(
        session_id="contemplator-handoff",
        turn_number=10,
        user_message="",
        helm_response="",
        context={
            "project": "hammerfall-solutions",
            "agent": "helm",
            "contemplator_writes": {
                "belief_patches": [],
                "personality_patches": [],
                "pattern_entries": [{"content": "Pattern observation: thing happens"}],
                "curiosity_flags": [],
            },
        },
    )

    await archivist_agent.handle(req, mock_router_for_summary, sb, mock_writer)

    # writer.write called for the pattern entry
    assert mock_writer.write.await_count >= 1
    pattern_calls = [
        c
        for c in mock_writer.write.await_args_list
        if c.kwargs.get("memory_type") and str(c.kwargs["memory_type"]).endswith("pattern")
    ]
    assert len(pattern_calls) == 1
    assert pattern_calls[0].kwargs["content"] == "Pattern observation: thing happens"

    # supabase.insert NOT called
    assert sb.insert.await_count == 0


async def test_archivist_contemplator_handoff_writes_reflection_through_monologue(
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
) -> None:
    """Reflection from Contemplator handoff routes through writer.write_monologue."""
    sb = MagicMock()
    sb.insert = AsyncMock(return_value={})

    req = InvokeRequest(
        session_id="contemplator-handoff",
        turn_number=10,
        user_message="",
        helm_response="",
        context={
            "project": "hammerfall-solutions",
            "agent": "helm",
            "contemplator_writes": {
                "belief_patches": [],
                "personality_patches": [],
                "pattern_entries": [],
                "curiosity_flags": [],
                "reflection": {"content": "I have been thinking about..."},
            },
        },
    )

    await archivist_agent.handle(req, mock_router_for_summary, sb, mock_writer)

    assert mock_writer.write_monologue.await_count == 1
    call_kwargs = mock_writer.write_monologue.await_args.kwargs
    assert call_kwargs["content"] == "I have been thinking about..."
    assert sb.insert.await_count == 0


async def test_archivist_contemplator_handoff_belief_patch_still_through_supabase(
    mock_router_for_summary: MagicMock,
    mock_writer: MagicMock,
) -> None:
    """Belief PATCH is sibling-table modify — stays through supabase per
    T0.B3 scope. Verification grep is INSERT/POST only; PATCHes are exempt."""
    sb = MagicMock()
    sb.select = AsyncMock(return_value=[{"id": "b1", "strength": 0.5}])
    sb.patch = AsyncMock(return_value=[])

    req = InvokeRequest(
        session_id="contemplator-handoff",
        turn_number=10,
        user_message="",
        helm_response="",
        context={
            "project": "hammerfall-solutions",
            "agent": "helm",
            "contemplator_writes": {
                "belief_patches": [{"id": "b1", "strength_delta": 0.1, "rationale": "test"}],
                "personality_patches": [],
                "pattern_entries": [],
                "curiosity_flags": [],
            },
        },
    )

    await archivist_agent.handle(req, mock_router_for_summary, sb, mock_writer)

    # Belief PATCH went through supabase, not writer
    assert sb.patch.await_count == 1
    sb.patch.assert_awaited_with("helm_beliefs", {"id": "b1"}, {"strength": 0.6})
