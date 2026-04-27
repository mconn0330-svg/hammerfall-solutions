"""Smoke tests for contemplator agent — verifies migration to PromptManager.

Contemplator is the first agent with TWO distinct prompt rows
(contemplator_pass_1 + contemplator_pass_2). Both must load before
either pass fires — a missing pass_2 prompt fails-fast at session_start
rather than mid-cycle on session_end.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import contemplator as contemplator_agent
from middleware import InvokeRequest


def _model_response(text: str) -> MagicMock:
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = text
    return r


@pytest.fixture
def mock_router() -> MagicMock:
    """Router stub — pass 1 returns minimal candidates JSON."""
    router = MagicMock()
    router.invoke = AsyncMock(
        return_value=_model_response(
            json.dumps(
                {
                    "belief_candidates": [],
                    "pattern_candidates": [],
                    "curiosity_candidates": [],
                    "personality_candidates": [],
                    "reflection_seed": "test",
                }
            )
        )
    )
    return router


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Supabase stub — every select returns empty (minimal snapshot)."""
    sb = MagicMock()
    sb.select = AsyncMock(return_value=[])
    return sb


@pytest.fixture
def mock_prompt_manager() -> MagicMock:
    """PromptManager stub — load returns canned prompts keyed by call order."""
    pm = MagicMock()
    pm.load = AsyncMock(return_value="STUB CONTEMPLATOR PROMPT")
    return pm


@pytest.fixture
def session_start_request() -> InvokeRequest:
    return InvokeRequest(
        session_id="contemp-test-session",
        turn_number=0,
        user_message="",
        helm_response="",
        context={
            "project": "hammerfall-solutions",
            "agent": "helm",
            "trigger": "session_start",
        },
    )


# ─── Prompt loading via PromptManager (T0.B5 extension) ─────────────────────


async def test_contemplator_loads_both_pass_prompts_at_invoke(
    session_start_request: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Both pass prompts load up-front so Pass 2 prompt unavailability
    surfaces at session_start, not mid-cycle on session_end."""
    await contemplator_agent.handle(
        session_start_request, mock_router, mock_supabase, mock_prompt_manager
    )

    # Both pass prompts loaded
    assert mock_prompt_manager.load.await_count == 2
    role_args = [c.args[0] for c in mock_prompt_manager.load.await_args_list]
    assert "contemplator_pass_1" in role_args
    assert "contemplator_pass_2" in role_args


async def test_contemplator_passes_loaded_pass1_prompt_to_model(
    session_start_request: InvokeRequest,
    mock_router: MagicMock,
    mock_supabase: MagicMock,
    mock_prompt_manager: MagicMock,
) -> None:
    """Pass 1 system message must contain the prompt loaded for
    contemplator_pass_1 — not a hardcoded constant."""

    # Different content per role so we can tell which one landed where
    async def load_side_effect(role: str, fallback_path: object = None) -> str:
        return f"PROMPT-FOR-{role.upper()}"

    mock_prompt_manager.load = AsyncMock(side_effect=load_side_effect)

    await contemplator_agent.handle(
        session_start_request, mock_router, mock_supabase, mock_prompt_manager
    )

    # Pass 1 model call — system message should contain the pass_1 prompt
    invoke_kwargs = mock_router.invoke.await_args.kwargs
    system_msg = next(m for m in invoke_kwargs["messages"] if m["role"] == "system")
    assert "PROMPT-FOR-CONTEMPLATOR_PASS_1" in system_msg["content"]
