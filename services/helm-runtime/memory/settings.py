"""Memory module settings — env-driven configuration.

Two paths for instantiation, both supported:

1. **Production runtime** — `main.py` constructs `MemorySettings` explicitly
   from values resolved by `model_router.py` (which already owns the
   Supabase URL/key from `config.yaml`). Keeps the runtime's existing
   single-source-of-truth pattern.

2. **Standalone CLI / tests** — `MemorySettings()` with no args auto-loads
   from env (HELM_MEMORY_* prefix) or a `.env` file at the repo root.
   Lets the `python -m memory.write` CLI (T0.B6) and pytest fixtures work
   without having to construct the full runtime first.

The `HELM_MEMORY_` prefix is deliberate — it scopes memory-module env vars
away from runtime-wide ones like `SUPABASE_BRAIN_URL`. In production they
should point at the same Supabase, but the namespace prevents accidental
cross-contamination between the runtime's read client and the memory
module's write client.

OS-aware default for `outbox_path` — `Path.home() / ".helm" / "outbox.db"`
works on Linux containers (helm user, `/home/helm/.helm/outbox.db`), macOS
dev, and Windows. v1's `/tmp/helm-outbox.jsonl` was Linux-only.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_outbox_path() -> Path:
    """SQLite outbox at ~/.helm/outbox.db. Cross-platform safe."""
    return Path.home() / ".helm" / "outbox.db"


class MemorySettings(BaseSettings):
    """Memory module configuration.

    Required:
        supabase_url            Supabase REST endpoint (e.g. https://xyz.supabase.co)
        supabase_service_key    Supabase service-role key

    Optional (with defaults):
        retry_attempts                  attempts on transient failure (network, 5xx)
        retry_backoff_base              initial backoff seconds (exponential)
        retry_backoff_max               cap on backoff (seconds)
        timeout_seconds                 per-request HTTP timeout
        circuit_breaker_threshold       consecutive failures before circuit opens
        circuit_breaker_cooldown        seconds the circuit stays open before half-open probe
        outbox_path                     SQLite outbox location (T0.B2 uses this)
    """

    model_config = SettingsConfigDict(
        env_prefix="HELM_MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str
    supabase_service_key: str
    retry_attempts: int = 3
    retry_backoff_base: float = 1.0
    retry_backoff_max: float = 30.0
    timeout_seconds: float = 10.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown: float = 30.0
    outbox_path: Path = _default_outbox_path()
