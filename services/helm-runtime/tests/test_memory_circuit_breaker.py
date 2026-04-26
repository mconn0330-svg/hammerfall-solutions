"""Tests for memory.circuit_breaker — state machine + observability hook."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from memory._time import utc_now
from memory.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
)

# ─── State machine ──────────────────────────────────────────────────────────


async def test_starts_closed() -> None:
    cb = CircuitBreaker()
    assert _state(cb) == "closed"
    assert cb.failure_count == 0


async def test_invalid_init_args_raise() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(threshold=0)
    with pytest.raises(ValueError):
        CircuitBreaker(cooldown_seconds=-1)


# Helper: compare via .value to bypass mypy's literal-type narrowing on
# property access — mypy can't see that record_failure() mutates cb._state,
# so successive equality checks against different enum members get flagged
# as comparison-overlap. String comparison is type-erased.
def _state(cb: CircuitBreaker) -> str:
    return cb.state.value


async def test_records_failures_until_threshold_then_opens() -> None:
    cb = CircuitBreaker(threshold=3, cooldown_seconds=30)
    # Record first two failures — circuit stays closed
    await cb.record_failure()
    await cb.record_failure()
    assert _state(cb) == "closed"
    # Third failure trips it
    await cb.record_failure()
    assert _state(cb) == "open"


async def test_open_circuit_blocks_calls() -> None:
    cb = CircuitBreaker(threshold=2, cooldown_seconds=60)
    await cb.record_failure()
    await cb.record_failure()
    assert _state(cb) == "open"
    with pytest.raises(CircuitBreakerOpen):
        await cb.before_call()


async def test_success_resets_failure_count_when_closed() -> None:
    cb = CircuitBreaker(threshold=5)
    await cb.record_failure()
    await cb.record_failure()
    assert cb.failure_count == 2
    await cb.record_success()
    assert cb.failure_count == 0
    assert _state(cb) == "closed"


async def test_open_circuit_transitions_to_half_open_after_cooldown() -> None:
    cb = CircuitBreaker(threshold=1, cooldown_seconds=10)
    await cb.record_failure()
    assert _state(cb) == "open"

    # Fast-forward time by manipulating _opened_at directly.
    cb._opened_at = utc_now() - timedelta(seconds=20)

    # before_call should now allow the probe and transition to HALF_OPEN
    await cb.before_call()
    assert _state(cb) == "half_open"


async def test_half_open_success_closes_circuit() -> None:
    cb = CircuitBreaker(threshold=1, cooldown_seconds=0)
    await cb.record_failure()
    # Cooldown is 0 — next before_call transitions to HALF_OPEN
    await cb.before_call()
    assert _state(cb) == "half_open"
    # Probe succeeded
    await cb.record_success()
    assert _state(cb) == "closed"
    assert cb.failure_count == 0


async def test_half_open_failure_reopens_immediately() -> None:
    """In HALF_OPEN, ANY failure re-opens — don't grant the next call a
    second probe credit."""
    cb = CircuitBreaker(threshold=5, cooldown_seconds=0)
    # Force open
    for _ in range(5):
        await cb.record_failure()
    assert _state(cb) == "open"
    # Probe transitions to HALF_OPEN
    await cb.before_call()
    assert _state(cb) == "half_open"
    # Probe failed — re-open immediately, regardless of failure_count
    await cb.record_failure()
    assert _state(cb) == "open"


async def test_open_message_includes_remaining_cooldown() -> None:
    cb = CircuitBreaker(threshold=1, cooldown_seconds=60)
    await cb.record_failure()
    with pytest.raises(CircuitBreakerOpen) as exc_info:
        await cb.before_call()
    msg = str(exc_info.value)
    assert "cooldown" in msg
    assert "remaining" in msg


# ─── Observability callback ─────────────────────────────────────────────────


async def test_callback_fires_on_state_change() -> None:
    transitions: list[CircuitState] = []

    cb = CircuitBreaker(
        threshold=2,
        cooldown_seconds=0,
        on_state_change=transitions.append,
    )
    # closed → open
    await cb.record_failure()
    await cb.record_failure()
    assert [t.value for t in transitions][-1] == "open"
    # open → half_open (via before_call)
    await cb.before_call()
    assert [t.value for t in transitions][-1] == "half_open"
    # half_open → closed (via success)
    await cb.record_success()
    assert [t.value for t in transitions][-1] == "closed"


async def test_callback_does_not_fire_on_no_change() -> None:
    """record_success on a CLOSED breaker doesn't trigger a transition."""
    transitions: list[CircuitState] = []
    cb = CircuitBreaker(threshold=3, on_state_change=transitions.append)
    await cb.record_success()
    assert transitions == []


async def test_callback_exception_does_not_break_breaker() -> None:
    """A bug in the callback MUST NOT prevent state transitions."""

    def boom(_state: CircuitState) -> None:
        raise RuntimeError("callback bug")

    cb = CircuitBreaker(threshold=1, on_state_change=boom)
    # Should not raise — callback exception is swallowed + logged
    await cb.record_failure()
    assert _state(cb) == "open"


# ─── Async safety ───────────────────────────────────────────────────────────


async def test_concurrent_failures_count_correctly() -> None:
    """100 concurrent record_failure calls — final count must be exactly 100."""
    cb = CircuitBreaker(threshold=1000)  # threshold high so circuit doesn't open
    await asyncio.gather(*(cb.record_failure() for _ in range(100)))
    assert cb.failure_count == 100
