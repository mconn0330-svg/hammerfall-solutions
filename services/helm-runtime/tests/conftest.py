"""Shared pytest fixtures for the helm-runtime test suite.

Tests must not hit the real Supabase brain or any external service. Fixtures
here provide stubs that satisfy the same interfaces.
"""

from typing import Any

import pytest


class _SupabaseStub:
    """In-memory stand-in for SupabaseClient. Async methods match the real
    interface so call sites don't need to know they're talking to a stub.
    Tests can override individual methods or read .calls to assert behavior.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name: str, args: tuple, kwargs: dict) -> None:
        self.calls.append((name, args, kwargs))

    async def insert(self, table: str, payload: dict) -> dict:
        self._record("insert", (table, payload), {})
        return payload

    async def patch(self, table: str, filters: dict, payload: dict) -> list:
        self._record("patch", (table, filters, payload), {})
        return [payload]

    async def delete(self, table: str, filters: dict) -> None:
        self._record("delete", (table, filters), {})

    async def select(self, table: str, params: dict) -> list:
        self._record("select", (table, params), {})
        return []

    async def rpc(self, function_name: str, params: dict) -> Any:
        self._record("rpc", (function_name, params), {})
        return None


@pytest.fixture
def supabase_stub() -> _SupabaseStub:
    """Fresh SupabaseClient stub per test. Tests may override methods or
    inspect .calls to assert what was sent to Supabase."""
    return _SupabaseStub()
