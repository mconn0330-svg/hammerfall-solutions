"""Circuit breaker for memory writes to Supabase.

Three states: CLOSED (normal), OPEN (failing — block calls fast), HALF_OPEN
(probe one call to see if the downstream recovered).

Every state transition emits a structured-log event AND invokes an optional
callback. T2.3 wires the callback to the SSE `system_health` event so the
UI's System tab surfaces circuit state in real time.

Async-safe: a single `asyncio.Lock` guards state transitions. Multiple
writers sharing one CircuitBreaker instance is the intended pattern.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum

from observability import get_logger

from ._time import utc_now

logger = get_logger("helm.memory.circuit_breaker")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted while the circuit is open.

    Caller should treat this as fail-fast: do not retry, do not sleep —
    the circuit will transition to HALF_OPEN automatically once cooldown
    elapses, and the next call after that will probe.
    """


# Callback fires on every state change (closed → open → half_open → closed).
# Wired to SSE in T2.3.
StateChangeCallback = Callable[[CircuitState], None]


class CircuitBreaker:
    """Async-safe circuit breaker.

    Usage:

        cb = CircuitBreaker(threshold=5, cooldown_seconds=30)
        await cb.before_call()       # raises CircuitBreakerOpen if open
        try:
            result = await downstream_call()
        except SomeFailure:
            await cb.record_failure()
            raise
        else:
            await cb.record_success()
    """

    def __init__(
        self,
        threshold: int = 5,
        cooldown_seconds: float = 30.0,
        on_state_change: StateChangeCallback | None = None,
    ) -> None:
        if threshold < 1:
            raise ValueError(f"threshold must be >= 1, got {threshold}")
        if cooldown_seconds < 0:
            raise ValueError(f"cooldown_seconds must be >= 0, got {cooldown_seconds}")
        self.threshold = threshold
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: datetime | None = None
        self._on_state_change = on_state_change
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def before_call(self) -> None:
        """Check whether a call is allowed. Raises CircuitBreakerOpen if not.

        Transitions OPEN → HALF_OPEN automatically when cooldown elapses.
        In HALF_OPEN the call IS allowed — it's the probe.
        """
        async with self._lock:
            if self._state != CircuitState.OPEN:
                return
            if self._opened_at is None:
                # Defensive — shouldn't happen, but don't deadlock if it does.
                return
            elapsed = utc_now() - self._opened_at
            if elapsed >= self.cooldown:
                self._set_state(CircuitState.HALF_OPEN)
                return
            remaining = (self.cooldown - elapsed).total_seconds()
            raise CircuitBreakerOpen(
                f"Circuit open for {elapsed.total_seconds():.1f}s "
                f"(cooldown {self.cooldown.total_seconds():.1f}s, "
                f"{remaining:.1f}s remaining)"
            )

    async def record_success(self) -> None:
        """Mark a call as succeeded.

        Resets failure count. Closes the circuit if it was HALF_OPEN (the
        probe worked) or OPEN (race-condition cleanup).
        """
        async with self._lock:
            self._failure_count = 0
            self._opened_at = None
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                self._set_state(CircuitState.CLOSED)

    async def record_failure(self) -> None:
        """Mark a call as failed. Opens the circuit if threshold exceeded.

        In HALF_OPEN, ANY failure re-opens immediately (the probe failed —
        downstream is still broken).
        """
        async with self._lock:
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN:
                self._opened_at = utc_now()
                self._set_state(CircuitState.OPEN)
                return
            if self._failure_count >= self.threshold:
                self._opened_at = utc_now()
                self._set_state(CircuitState.OPEN)

    def _set_state(self, new_state: CircuitState) -> None:
        """Internal state-change hook — logs + invokes callback. Caller
        already holds the lock."""
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        if new_state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker.opened",
                consecutive_failures=self._failure_count,
                cooldown_seconds=self.cooldown.total_seconds(),
                from_state=old.value,
            )
        elif new_state == CircuitState.HALF_OPEN:
            logger.info("circuit_breaker.half_open", from_state=old.value)
        elif new_state == CircuitState.CLOSED:
            logger.info("circuit_breaker.closed", from_state=old.value)
        if self._on_state_change is not None:
            try:
                self._on_state_change(new_state)
            except Exception:
                # Callback bugs MUST NOT break the breaker. Log + continue.
                logger.exception("circuit_breaker.callback_error")
