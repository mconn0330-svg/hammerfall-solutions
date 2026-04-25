"""Smoke test — proves the test harness wires up correctly.

If this passes, pytest + pytest-asyncio + the project import path all work.
Real coverage starts arriving with T0.B1 (memory module).
"""

from typing import Any


def test_main_module_imports() -> None:
    """The runtime entrypoint imports without raising."""
    import main

    assert hasattr(main, "__doc__")


async def test_async_mode_works() -> None:
    """pytest-asyncio is configured with asyncio_mode='auto' — async tests
    run without an explicit @pytest.mark.asyncio decorator."""
    assert True


def test_supabase_stub_records_calls(supabase_stub: Any) -> None:
    """The conftest supabase_stub fixture is wired and records calls."""
    assert supabase_stub.calls == []
