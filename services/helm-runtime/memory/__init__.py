"""Memory module — the unified write path for Helm's brain.

T0.B1 establishes the foundation:
  - `MemoryType` enum + `MemoryEntry` Pydantic model + `slugify` utility
  - `MemorySettings` (env-driven, `HELM_MEMORY_` prefix)
  - `CircuitBreaker` with state-change observability hooks
  - `MemoryClient` (httpx + retry + circuit breaker + tracing)
  - `MemoryWriter` (`write()` + type-specific helpers)

Subsequent T0.B work:
  - T0.B2 layers an outbox underneath the client
  - T0.B3 migrates in-process agents to write through this module
  - T0.B5b moves runtime tunables into config.yaml
  - T0.B6 deletes brain.sh + script orphans + strips surface assumptions
  - T0.B7 adds Tier 2 types by appending to `MemoryType` + thin wrappers

Public API — anything not exported here is internal. Keep imports stable
across T0.B PRs; downstream consumers (agents) bind to this surface.
"""

from __future__ import annotations

from ._time import utc_now
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    StateChangeCallback,
)
from .client import MemoryClient, MemoryClientError, MemoryWriteFailed
from .models import MemoryEntry, MemoryType, slugify
from .outbox import DrainResult, Outbox, OutboxStats, stop_drain_loop
from .settings import MemorySettings
from .writer import MemoryWriter

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
    "DrainResult",
    "MemoryClient",
    "MemoryClientError",
    "MemoryEntry",
    "MemorySettings",
    "MemoryType",
    "MemoryWriteFailed",
    "MemoryWriter",
    "Outbox",
    "OutboxStats",
    "StateChangeCallback",
    "slugify",
    "stop_drain_loop",
    "utc_now",
]
