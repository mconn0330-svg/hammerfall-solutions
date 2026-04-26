"""Tests for scripts/cost_summary.py (T0.A15).

Module is at `scripts/cost_summary.py`. We add `scripts/` to sys.path so
the test can import it without packaging it as a module.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import cost_summary  # noqa: E402

TODAY = date(2026, 4, 28)  # Tuesday — so window is Tue 21 → Mon 27


def _events(*specs: tuple[str, str, float]) -> list[tuple[date, str, float]]:
    """Helper: build an event list from (iso_date, model, cost) tuples."""
    return [(date.fromisoformat(d), m, c) for (d, m, c) in specs]


def test_empty_input_produces_signal_of_life_summary() -> None:
    out = cost_summary.summarize([], TODAY)
    assert "Weekly cost summary" in out
    assert "No `cost.recorded` events" in out
    # Should namedrop T2.3 so the reader knows why it's empty.
    assert "T2.3" in out


def test_single_event_summarizes_correctly() -> None:
    events = _events(("2026-04-22", "claude-opus-4-7", 1.23))
    out = cost_summary.summarize(events, TODAY)
    assert "$1.23" in out
    assert "claude-opus-4-7" in out
    assert "first week with cost data" in out  # no prior baseline


def test_week_over_week_delta_increase() -> None:
    events = _events(
        ("2026-04-15", "claude-opus-4-7", 5.00),  # prior week
        ("2026-04-22", "claude-opus-4-7", 7.50),  # this week
    )
    out = cost_summary.summarize(events, TODAY)
    assert "$7.50" in out
    assert "+50.0%" in out


def test_week_over_week_delta_decrease() -> None:
    events = _events(
        ("2026-04-15", "claude-opus-4-7", 10.00),  # prior week
        ("2026-04-22", "claude-opus-4-7", 4.00),  # this week
    )
    out = cost_summary.summarize(events, TODAY)
    assert "-60.0%" in out


def test_top_spend_days_section() -> None:
    events = _events(
        ("2026-04-22", "claude-opus-4-7", 0.50),
        ("2026-04-23", "claude-opus-4-7", 2.00),  # spike
        ("2026-04-24", "claude-opus-4-7", 0.30),
        ("2026-04-25", "claude-sonnet-4-6", 0.10),
        ("2026-04-26", "claude-opus-4-7", 1.00),
    )
    out = cost_summary.summarize(events, TODAY)
    assert "Top spend days" in out
    # Highest day should appear first in the table.
    spike_idx = out.index("2026-04-23")
    later_idx = out.index("2026-04-22")
    assert spike_idx < later_idx


def test_by_model_breakdown_sorted_descending() -> None:
    events = _events(
        ("2026-04-22", "claude-sonnet-4-6", 0.10),
        ("2026-04-22", "claude-opus-4-7", 5.00),
    )
    out = cost_summary.summarize(events, TODAY)
    opus_idx = out.index("claude-opus-4-7")
    sonnet_idx = out.index("claude-sonnet-4-6")
    assert opus_idx < sonnet_idx, "more-expensive model should appear first"


def test_monthly_projection() -> None:
    events = _events(("2026-04-22", "claude-opus-4-7", 10.00))
    out = cost_summary.summarize(events, TODAY)
    # 10.00 × 4.3 = 43.00
    assert "$43.00" in out


def test_load_events_handles_missing_file(tmp_path: Path) -> None:
    out = cost_summary._load_events(tmp_path / "nope.json")
    assert out == []


def test_load_events_handles_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json {")
    out = cost_summary._load_events(bad)
    assert out == []


def test_load_events_filters_non_cost_events(tmp_path: Path) -> None:
    f = tmp_path / "mixed.json"
    f.write_text(
        json.dumps(
            [
                {
                    "event": "cost.recorded",
                    "timestamp": "2026-04-22T10:00:00Z",
                    "model": "claude-opus-4-7",
                    "cost": 1.0,
                },
                {
                    "event": "rate.warn",
                    "timestamp": "2026-04-22T11:00:00Z",
                },  # not a cost event
                {
                    "event": "cost.recorded",
                    "timestamp": "bad",  # malformed timestamp
                    "model": "x",
                    "cost": 1.0,
                },
            ]
        )
    )
    out = cost_summary._load_events(f)
    assert len(out) == 1
    assert out[0][1] == "claude-opus-4-7"


@pytest.mark.parametrize(
    "iso, expected_model, expected_cost",
    [
        ("2026-04-22T12:00:00Z", "x", 1.5),
        ("2026-04-22T12:00:00+00:00", "x", 1.5),
    ],
)
def test_parse_event_handles_timestamp_formats(
    iso: str, expected_model: str, expected_cost: float
) -> None:
    raw = {
        "event": "cost.recorded",
        "timestamp": iso,
        "model": expected_model,
        "cost": expected_cost,
    }
    out = cost_summary._parse_event(raw)
    assert out is not None
    assert out[1] == expected_model
    assert out[2] == expected_cost
