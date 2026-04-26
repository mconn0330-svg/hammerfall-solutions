"""Tests for memory._time."""

from __future__ import annotations

from datetime import UTC

from memory._time import utc_now


def test_utc_now_returns_timezone_aware_datetime() -> None:
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo.utcoffset(now) == UTC.utcoffset(now)


def test_utc_now_is_in_utc() -> None:
    """The whole point of the helper: never naive, always UTC."""
    now = utc_now()
    assert now.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_utc_now_increases_monotonically() -> None:
    """Two consecutive calls produce distinct, ordered timestamps."""
    a = utc_now()
    b = utc_now()
    assert b >= a
