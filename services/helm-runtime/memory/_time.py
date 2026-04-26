"""UTC-aware datetime helpers.

Centralized so the deprecated `datetime.utcnow()` (returns naive datetime in
Python 3.12+, deprecation in PEP 681) cannot sneak back in. Memory entries
have to be timezone-aware end-to-end — Supabase `timestamptz` columns store
UTC, and a naive datetime would be silently treated as the server's local
zone, producing off-by-hours bugs that don't surface until much later.

Single source of truth: every `created_at` / `last_attempt_at` / etc. across
the memory module routes through `utc_now()`.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)
