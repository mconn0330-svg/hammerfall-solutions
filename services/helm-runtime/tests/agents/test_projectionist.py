"""Smoke tests for projectionist agent — verifies migration to MemoryWriter.

Per V2 spec T0.B3: each agent gets a smoke test that mocks the memory module
and asserts the agent calls memory.write* with expected args. This is the
regression net for ""did the agent migration actually route writes through
the memory module"" — the verification grep catches static call shapes; this
catches semantic-correctness (right table, right payload).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import projectionist as projectionist_agent
from middleware import InvokeRequest


@pytest.fixture
def request_obj() -> InvokeRequest:
    return InvokeRequest(
        session_id="test-session-uuid",
        turn_number=3,
        user_message="Test user message",
        helm_response="Test helm response",
        context={"project": "hammerfall-solutions", "agent": "helm"},
    )


@pytest.fixture
def mock_router() -> MagicMock:
    """Router stub — invoke returns a canned JSON-mode response."""
    router = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps(
        {
            "turn": 3,
            "timestamp": "2026-04-26T14:00:00Z",
            "user_id": "maxwell",
            "session_id": "test-session-uuid",
            "user": "Test user message",
            "helm": "Test helm response",
            "topic": "test topic",
            "domain": "process",
            "entities_mentioned": [],
            "belief_links": [],
            "frame_status": "active",
            "superseded_reason": None,
            "superseded_at_turn": None,
        }
    )
    router.invoke = AsyncMock(return_value=response)
    return router


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Supabase stub — select returns empty (no offload triggered)."""
    sb = MagicMock()
    sb.select = AsyncMock(return_value=[])
    sb.patch = AsyncMock(return_value=[])
    return sb


@pytest.fixture
def mock_writer() -> MagicMock:
    """MemoryWriter stub — records every write_helm_frame_record call."""
    w = MagicMock()
    w.write_helm_frame_record = AsyncMock(
        return_value={"session_id": "test-session-uuid", "turn_number": 3}
    )
    return w


@pytest.fixture
def mock_prompt_manager() -> MagicMock:
    """PromptManager stub — load() returns a canned system prompt."""
    pm = MagicMock()
    pm.load = AsyncMock(return_value="STUB PROJECTIONIST SYSTEM PROMPT")
    return pm


async def test_projectionist_writes_helm_frame_through_memory_writer(
    request_obj: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """The migration target: Projectionist no longer calls supabase.insert
    directly; it routes through MemoryWriter.write_helm_frame_record."""
    await projectionist_agent.handle(
        request_obj, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    # The write went through MemoryWriter, not supabase.insert
    assert mock_writer.write_helm_frame_record.await_count == 1
    call_kwargs = mock_writer.write_helm_frame_record.await_args.kwargs

    assert call_kwargs["session_id"] == "test-session-uuid"
    assert call_kwargs["turn_number"] == 3
    assert call_kwargs["layer"] == "warm"
    assert call_kwargs["frame_status"] == "active"
    assert call_kwargs["frame_json"]["topic"] == "test topic"
    assert call_kwargs["frame_json"]["session_id"] == "test-session-uuid"


async def test_projectionist_does_not_call_supabase_insert(
    request_obj: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Verification grep equivalent — supabase.insert must not be called by
    the post-migration handler. PATCHes (frame_status updates) and SELECTs
    (offload trigger checks) are still allowed through supabase."""
    mock_supabase.insert = AsyncMock(return_value={})

    await projectionist_agent.handle(
        request_obj, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    assert mock_supabase.insert.await_count == 0


async def test_projectionist_resolution_pass_skips_writer(
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Resolution pass is a different code path — no model call, no
    writer.write_helm_frame_record. Just supabase PATCHes (status transitions)."""
    req = InvokeRequest(
        session_id="test-session-uuid",
        turn_number=10,
        user_message="[SESSION-END-RESOLUTION]",
        helm_response="[SESSION-END-RESOLUTION]",
        context={
            "project": "hammerfall-solutions",
            "agent": "helm",
            "resolution_pass": True,
        },
    )

    await projectionist_agent.handle(
        req, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    # Resolution pass: no new frame created, so writer is not called
    assert mock_writer.write_helm_frame_record.await_count == 0
    # Model not invoked either — resolution is pure SQL ops
    assert mock_router.invoke.await_count == 0


async def test_projectionist_uses_request_session_id_not_model_output(
    request_obj: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Even if the model hallucinates a different session_id, the handler
    overrides with req.session_id. Catches a class of frame-attribution bugs
    where the model name-collides on session ids."""
    # Have the model return a different session_id
    response = mock_router.invoke.return_value
    payload: dict[str, Any] = json.loads(response.choices[0].message.content)
    payload["session_id"] = "MODEL-HALLUCINATED-DIFFERENT-ID"
    response.choices[0].message.content = json.dumps(payload)

    await projectionist_agent.handle(
        request_obj, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    call_kwargs = mock_writer.write_helm_frame_record.await_args.kwargs
    assert call_kwargs["session_id"] == "test-session-uuid"
    assert call_kwargs["frame_json"]["session_id"] == "test-session-uuid"


# ─── Prompt loading via PromptManager (T0.B5 extension) ─────────────────────


async def test_projectionist_loads_prompt_via_prompt_manager(
    request_obj: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Projectionist must call prompt_manager.load("projectionist", ...) — proves
    the migration to centralized prompt loading actually fires."""
    await projectionist_agent.handle(
        request_obj, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    assert mock_prompt_manager.load.await_count == 1
    role_arg = mock_prompt_manager.load.await_args.args[0]
    assert role_arg == "projectionist"


async def test_projectionist_passes_loaded_prompt_to_model(
    request_obj: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_writer: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """The system prompt the model sees must come from PromptManager's
    return value — not a hardcoded SYSTEM_PROMPT constant."""
    mock_prompt_manager.load = AsyncMock(return_value="UNIQUELY-LOADED-PROMPT-STRING")

    await projectionist_agent.handle(
        request_obj, mock_router, mock_supabase, mock_writer, mock_prompt_manager
    )

    invoke_kwargs = mock_router.invoke.await_args.kwargs
    system_msg = next(m for m in invoke_kwargs["messages"] if m["role"] == "system")
    assert "UNIQUELY-LOADED-PROMPT-STRING" in system_msg["content"]
