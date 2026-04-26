"""Tests for memory.client — retry, circuit breaker integration, error mapping."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from memory.circuit_breaker import CircuitBreakerOpen, CircuitState
from memory.client import MemoryClient, MemoryWriteFailed
from memory.settings import MemorySettings


def _make_settings(**overrides: Any) -> MemorySettings:
    """Test settings with fast-fail defaults — no real Supabase."""
    base: dict[str, Any] = {
        "supabase_url": "https://test.supabase.co",
        "supabase_service_key": "test-key",
        "retry_attempts": 3,
        "retry_backoff_base": 0.0,  # zero delay so tests don't block
        "retry_backoff_max": 0.0,
        "timeout_seconds": 1.0,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_cooldown": 0.0,
    }
    base.update(overrides)
    return MemorySettings(**base)


def _httpx_mock(handler: Any) -> httpx.MockTransport:
    """Wrap a handler function as an httpx MockTransport."""
    return httpx.MockTransport(handler)


# ─── Happy path ─────────────────────────────────────────────────────────────


async def test_insert_returns_supabase_row_on_success() -> None:
    """PostgREST returns a list when Prefer=return=representation; we
    unwrap to the first row."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"id": "abc", "content": "hello"}],
            request=request,
        )

    client = MemoryClient(_make_settings())
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    result = await client.insert("helm_memory", {"content": "hello"})
    assert result == {"id": "abc", "content": "hello"}

    await client.aclose()


async def test_insert_unwraps_dict_response() -> None:
    """Some configs return a dict directly — handle both shapes."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "abc"}, request=request)

    client = MemoryClient(_make_settings())
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    result = await client.insert("helm_memory", {"content": "x"})
    assert result == {"id": "abc"}
    await client.aclose()


# ─── Retry behavior ─────────────────────────────────────────────────────────


async def test_insert_retries_on_5xx_until_success() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            return httpx.Response(503, json={"error": "transient"}, request=request)
        return httpx.Response(200, json=[{"ok": True}], request=request)

    client = MemoryClient(_make_settings(retry_attempts=5))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    result = await client.insert("helm_memory", {"x": 1})
    assert result == {"ok": True}
    assert len(attempts) == 3
    await client.aclose()


async def test_insert_raises_after_exhausting_retries_on_5xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"}, request=request)

    client = MemoryClient(_make_settings(retry_attempts=2))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    with pytest.raises(MemoryWriteFailed) as exc_info:
        await client.insert("helm_memory", {"x": 1})
    assert exc_info.value.attempts == 2
    await client.aclose()


async def test_insert_does_not_retry_on_4xx() -> None:
    """4xx is a caller bug (validation, RLS) — fail fast, don't waste retries."""
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(400, json={"error": "bad payload"}, request=request)

    client = MemoryClient(_make_settings(retry_attempts=5))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    with pytest.raises(MemoryWriteFailed) as exc_info:
        await client.insert("helm_memory", {"bad": True})
    assert len(attempts) == 1  # exactly one try — no retries
    assert exc_info.value.attempts == 1
    await client.aclose()


async def test_insert_retries_on_network_error() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 2:
            raise httpx.ConnectError("simulated", request=request)
        return httpx.Response(200, json=[{"ok": True}], request=request)

    client = MemoryClient(_make_settings(retry_attempts=3))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    result = await client.insert("helm_memory", {"x": 1})
    assert result == {"ok": True}
    assert len(attempts) == 2
    await client.aclose()


# ─── Circuit breaker integration ────────────────────────────────────────────


async def test_4xx_records_failure_against_circuit_breaker() -> None:
    """A 4xx counts as one failure — repeated 4xx eventually opens the circuit."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad"}, request=request)

    client = MemoryClient(_make_settings(circuit_breaker_threshold=3))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    for _ in range(3):
        with pytest.raises(MemoryWriteFailed):
            await client.insert("helm_memory", {"x": 1})

    assert client.circuit_breaker.state == CircuitState.OPEN
    await client.aclose()


async def test_open_circuit_blocks_subsequent_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"}, request=request)

    client = MemoryClient(
        _make_settings(retry_attempts=1, circuit_breaker_threshold=2, circuit_breaker_cooldown=60)
    )
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    # Two failed writes — circuit opens
    for _ in range(2):
        with pytest.raises(MemoryWriteFailed):
            await client.insert("helm_memory", {"x": 1})
    assert client.circuit_breaker.state == CircuitState.OPEN

    # Third call should fail fast with CircuitBreakerOpen, NOT MemoryWriteFailed
    with pytest.raises(CircuitBreakerOpen):
        await client.insert("helm_memory", {"x": 1})

    await client.aclose()


async def test_success_after_failures_resets_breaker_count() -> None:
    """A successful write between failures resets the consecutive-failure
    counter — failures must be CONSECUTIVE to open the circuit."""
    state = {"fail_next": True}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["fail_next"]:
            state["fail_next"] = False
            return httpx.Response(503, json={"error": "down"}, request=request)
        return httpx.Response(200, json=[{"ok": True}], request=request)

    client = MemoryClient(_make_settings(retry_attempts=1, circuit_breaker_threshold=3))
    client._http = httpx.AsyncClient(transport=_httpx_mock(handler))

    # First call fails
    with pytest.raises(MemoryWriteFailed):
        await client.insert("helm_memory", {"x": 1})
    assert client.circuit_breaker.failure_count == 1

    # Second call succeeds — counter resets
    await client.insert("helm_memory", {"x": 2})
    assert client.circuit_breaker.failure_count == 0
    assert client.circuit_breaker.state == CircuitState.CLOSED

    await client.aclose()


# ─── Backoff math ───────────────────────────────────────────────────────────


def test_compute_backoff_grows_exponentially() -> None:
    client = MemoryClient(_make_settings(retry_backoff_base=1.0, retry_backoff_max=100.0))
    assert client._compute_backoff(0) == 1.0
    assert client._compute_backoff(1) == 2.0
    assert client._compute_backoff(2) == 4.0
    assert client._compute_backoff(3) == 8.0


def test_compute_backoff_caps_at_max() -> None:
    client = MemoryClient(_make_settings(retry_backoff_base=1.0, retry_backoff_max=5.0))
    # Without cap: 1, 2, 4, 8, 16. With cap=5: 1, 2, 4, 5, 5.
    assert client._compute_backoff(3) == 5.0
    assert client._compute_backoff(10) == 5.0
