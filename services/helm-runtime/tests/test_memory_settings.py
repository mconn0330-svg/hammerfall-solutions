"""Tests for memory.settings — env loading, defaults, validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from memory.settings import MemorySettings


# Fixture: clear all HELM_MEMORY_* env vars before each test so we don't
# inherit machine-local state. The settings module reads env at instantiation;
# tests need a clean slate.
@pytest.fixture(autouse=True)
def _clear_helm_memory_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in list(os.environ.keys()):
        if key.startswith("HELM_MEMORY_"):
            monkeypatch.delenv(key, raising=False)


def test_explicit_construction_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production path — runtime constructs MemorySettings from values
    resolved by model_router.py, ignoring env."""
    monkeypatch.setenv("HELM_MEMORY_SUPABASE_URL", "https://from-env.supabase.co")
    s = MemorySettings(
        supabase_url="https://from-arg.supabase.co",
        supabase_service_key="explicit-key",
    )
    assert s.supabase_url == "https://from-arg.supabase.co"
    assert s.supabase_service_key == "explicit-key"


def test_env_loads_when_no_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Standalone path — CLI/tests instantiate with no args, env supplies."""
    monkeypatch.setenv("HELM_MEMORY_SUPABASE_URL", "https://env.supabase.co")
    monkeypatch.setenv("HELM_MEMORY_SUPABASE_SERVICE_KEY", "env-key")
    s = MemorySettings()
    assert s.supabase_url == "https://env.supabase.co"
    assert s.supabase_service_key == "env-key"


def test_missing_required_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required fields with no env, no args — Pydantic raises."""
    with pytest.raises(ValidationError):
        MemorySettings()


def test_optional_defaults_are_sensible() -> None:
    """Defaults match the V2 spec values."""
    s = MemorySettings(
        supabase_url="https://x.supabase.co",
        supabase_service_key="k",
    )
    assert s.retry_attempts == 3
    assert s.retry_backoff_base == 1.0
    assert s.retry_backoff_max == 30.0
    assert s.timeout_seconds == 10.0
    assert s.circuit_breaker_threshold == 5
    assert s.circuit_breaker_cooldown == 30.0
    # outbox path is OS-aware
    assert s.outbox_path == Path.home() / ".helm" / "outbox.db"


def test_env_overrides_optional_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """All HELM_MEMORY_* vars override the corresponding setting."""
    monkeypatch.setenv("HELM_MEMORY_SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("HELM_MEMORY_SUPABASE_SERVICE_KEY", "k")
    monkeypatch.setenv("HELM_MEMORY_RETRY_ATTEMPTS", "7")
    monkeypatch.setenv("HELM_MEMORY_TIMEOUT_SECONDS", "5.0")
    monkeypatch.setenv("HELM_MEMORY_CIRCUIT_BREAKER_THRESHOLD", "10")

    s = MemorySettings()
    assert s.retry_attempts == 7
    assert s.timeout_seconds == 5.0
    assert s.circuit_breaker_threshold == 10


def test_extra_env_vars_ignored() -> None:
    """extra='ignore' — random env doesn't crash construction."""
    s = MemorySettings(
        supabase_url="https://x.supabase.co",
        supabase_service_key="k",
        not_a_real_field="value",
    )
    assert s.supabase_url == "https://x.supabase.co"
