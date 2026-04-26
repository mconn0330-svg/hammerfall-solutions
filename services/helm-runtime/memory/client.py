"""HTTP client for Supabase memory writes.

Wraps `httpx.AsyncClient` with:
  - Configurable retry (exponential backoff with cap)
  - Circuit breaker (open after N consecutive failures, see circuit_breaker.py)
  - OpenTelemetry tracing on every call
  - Structured log events on success / retry / failure / circuit transitions

This is the WRITE-side client. Reads still go through `supabase_client.py`
(renamed `read_client.py` in T0.B6 per the V2 spec). The split is durable:
this module enforces write-side guarantees (retry, breaker, outbox seam)
that the read client doesn't need.

T0.B2 layers an outbox underneath: `MemoryClient.insert()` becomes the
fast path, with the outbox as the durable backstop on persistent failure.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from observability import get_logger, tracer

from .circuit_breaker import CircuitBreaker, StateChangeCallback
from .settings import MemorySettings

logger = get_logger("helm.memory.client")


class MemoryClientError(Exception):
    """Base error from MemoryClient."""


class MemoryWriteFailed(MemoryClientError):
    """Raised when a write fails after exhausting retries.

    `attempts` records how many tries were made before giving up — useful for
    outbox bookkeeping in T0.B2.
    """

    def __init__(self, message: str, attempts: int):
        super().__init__(message)
        self.attempts = attempts


class MemoryClient:
    """Async HTTP client for write operations against Supabase REST.

    Holds a single `httpx.AsyncClient` internally for connection reuse.
    Caller closes via `aclose()` at service shutdown.

    Threading: async-safe across tasks. The underlying httpx client is
    designed for concurrent use; the circuit breaker guards its own state
    with an asyncio.Lock.
    """

    def __init__(
        self,
        settings: MemorySettings,
        circuit_breaker_callback: StateChangeCallback | None = None,
    ) -> None:
        self._settings = settings
        self._url = settings.supabase_url.rstrip("/")
        self._headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._http = httpx.AsyncClient(timeout=settings.timeout_seconds)
        self._cb = CircuitBreaker(
            threshold=settings.circuit_breaker_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown,
            on_state_change=circuit_breaker_callback,
        )

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._cb

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST one row. Retries on transient failures, opens circuit on
        consecutive failures.

        Raises:
            CircuitBreakerOpen: circuit is open — fail fast, don't retry.
            MemoryWriteFailed: 4xx (client error, not retried) or
                                5xx/network (retried, then failed).
        """
        url = f"{self._url}/rest/v1/{table}"
        last_error: Exception | None = None

        with tracer.start_as_current_span("memory.client.insert") as span:
            span.set_attribute("memory.table", table)

            # Circuit check is one-shot per call, before the retry loop.
            # Retries are part of a single logical "call" — if the circuit
            # is open at the start, we don't even try.
            await self._cb.before_call()

            for attempt in range(self._settings.retry_attempts):
                try:
                    response = await self._http.post(url, json=payload, headers=self._headers)
                    response.raise_for_status()
                    body = response.json()
                    # PostgREST returns a list when Prefer=return=representation
                    inserted: dict[str, Any] = body[0] if isinstance(body, list) and body else body
                    await self._cb.record_success()
                    span.set_attribute("memory.attempts", attempt + 1)
                    logger.info(
                        "memory.write.success",
                        table=table,
                        attempts=attempt + 1,
                    )
                    return inserted
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    last_error = e
                    backoff = self._compute_backoff(attempt)
                    logger.warning(
                        "memory.write.retry",
                        table=table,
                        attempt=attempt + 1,
                        backoff_seconds=backoff,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    if attempt < self._settings.retry_attempts - 1:
                        await asyncio.sleep(backoff)
                except httpx.HTTPStatusError as e:
                    # 4xx: client error — not retriable. Caller bug
                    # (validation, RLS, malformed payload). Open the circuit
                    # only on the first 4xx to avoid silent retries; release
                    # the call to the caller immediately.
                    if 400 <= e.response.status_code < 500:
                        await self._cb.record_failure()
                        logger.error(
                            "memory.write.client_error",
                            table=table,
                            status=e.response.status_code,
                            body=e.response.text[:500],
                        )
                        raise MemoryWriteFailed(
                            f"Supabase returned {e.response.status_code}: "
                            f"{e.response.text[:200]}",
                            attempts=attempt + 1,
                        ) from e
                    # 5xx: server error — retriable
                    last_error = e
                    backoff = self._compute_backoff(attempt)
                    logger.warning(
                        "memory.write.retry",
                        table=table,
                        attempt=attempt + 1,
                        backoff_seconds=backoff,
                        status=e.response.status_code,
                    )
                    if attempt < self._settings.retry_attempts - 1:
                        await asyncio.sleep(backoff)

            # Exhausted retries — record failure for circuit breaker
            await self._cb.record_failure()
            span.set_attribute("memory.attempts", self._settings.retry_attempts)
            logger.error(
                "memory.write.failed",
                table=table,
                attempts=self._settings.retry_attempts,
                error=str(last_error) if last_error else "unknown",
            )
            raise MemoryWriteFailed(
                f"Write to {table} failed after "
                f"{self._settings.retry_attempts} attempts: {last_error}",
                attempts=self._settings.retry_attempts,
            )

    def _compute_backoff(self, attempt: int) -> float:
        """Exponential backoff capped at retry_backoff_max."""
        base: float = self._settings.retry_backoff_base
        cap: float = self._settings.retry_backoff_max
        return float(min(base * (2**attempt), cap))

    async def aclose(self) -> None:
        """Close the underlying HTTP client. Call at service shutdown."""
        await self._http.aclose()
