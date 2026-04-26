#!/usr/bin/env python3
"""
T0.A15 — Cost summary.

Reads `helm.cost` structured log events (JSON array) and produces a markdown
summary suitable for a GitHub issue body. Pairs with T0.A11's DollarCap which
emits the `cost.recorded` events.

Input format (one JSON object per event in a list):

    [
      {
        "timestamp": "2026-04-25T12:34:56Z",
        "event": "cost.recorded",
        "model": "claude-opus-4-7",
        "cost": 0.0234,
        "day_total": 1.23
      },
      ...
    ]

Output (markdown to stdout): total spend / by-model breakdown / top 5 spike
days / week-over-week delta / monthly projection at current rate.

Empty input is handled gracefully — produces a "no cost events recorded"
summary so the weekly issue still opens (signal-of-life), just with nothing
to report. This is the expected state at T1 until T2.3 wires the provider
chain to actually emit cost events.

Usage:
    python3 scripts/cost_summary.py cost_events.json > summary.md
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def _parse_event(raw: dict[str, Any]) -> tuple[date, str, float] | None:
    """Convert a raw log event dict to (date, model, cost). Returns None
    if the event isn't a cost.recorded event or is missing required fields."""
    if raw.get("event") != "cost.recorded":
        return None
    try:
        ts = datetime.fromisoformat(raw["timestamp"].replace("Z", "+00:00"))
        return ts.date(), str(raw["model"]), float(raw["cost"])
    except (KeyError, ValueError, TypeError):
        return None


def _load_events(path: Path) -> list[tuple[date, str, float]]:
    """Read the JSON file and return parsed cost events.
    Empty / missing / malformed file → empty list (logged to stderr)."""
    if not path.exists():
        print(f"warning: {path} does not exist; treating as empty", file=sys.stderr)
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(
            f"warning: {path} is not valid JSON: {e}; treating as empty",
            file=sys.stderr,
        )
        return []
    if not isinstance(raw, list):
        print(
            f"warning: {path} is not a JSON array; treating as empty", file=sys.stderr
        )
        return []
    parsed = [event for event in (_parse_event(r) for r in raw) if event is not None]
    return parsed


def summarize(events: list[tuple[date, str, float]], today: date) -> str:
    """Build the markdown summary. `today` is injected for testability —
    prod calls pass `date.today()`; tests pass a fixed date."""
    if not events:
        return (
            "# Weekly cost summary\n\n"
            "_No `cost.recorded` events were recorded in the last 7 days._\n\n"
            "Expected at T1 until T2.3 wires the provider chain into "
            "`DollarCap.check_and_record()` and a log destination ships cost "
            "events to this workflow's fetch source. See "
            "`docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A15.\n"
        )

    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)

    this_week = [(d, m, c) for (d, m, c) in events if week_ago <= d < today]
    prior_week = [(d, m, c) for (d, m, c) in events if two_weeks_ago <= d < week_ago]

    total_this_week = sum(c for (_, _, c) in this_week)
    total_prior_week = sum(c for (_, _, c) in prior_week)

    by_model: dict[str, float] = defaultdict(float)
    for _, model, cost in this_week:
        by_model[model] += cost

    by_day: dict[date, float] = defaultdict(float)
    for d, _, cost in this_week:
        by_day[d] += cost

    top_days = sorted(by_day.items(), key=lambda kv: kv[1], reverse=True)[:5]

    if total_prior_week > 0:
        wow_delta_pct = ((total_this_week - total_prior_week) / total_prior_week) * 100
        wow_str = f"{wow_delta_pct:+.1f}% vs prior week (${total_prior_week:.2f})"
    elif total_this_week > 0:
        wow_str = "first week with cost data — no prior baseline"
    else:
        wow_str = "no spend this week or last"

    monthly_projection = total_this_week * 4.3  # ~4.3 weeks per month

    lines: list[str] = [
        "# Weekly cost summary",
        "",
        f"Window: {week_ago.isoformat()} → {(today - timedelta(days=1)).isoformat()}",
        "",
        f"**Total this week:** ${total_this_week:.2f}",
        f"**Week-over-week:** {wow_str}",
        f"**Monthly projection at current rate:** ${monthly_projection:.2f}",
        "",
        "## By model",
        "",
        "| Model | Spend |",
        "| --- | --- |",
    ]
    for model, cost in sorted(by_model.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"| `{model}` | ${cost:.4f} |")

    lines.extend(
        ["", "## Top spend days (this week)", "", "| Date | Spend |", "| --- | --- |"]
    )
    for day, cost in top_days:
        lines.append(f"| {day.isoformat()} | ${cost:.4f} |")

    if len(this_week) >= 7:
        daily_costs = list(by_day.values())
        avg = statistics.mean(daily_costs)
        lines.extend(
            [
                "",
                f"_Daily average: ${avg:.4f} across {len(daily_costs)} day(s) with spend._",
            ]
        )

    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: cost_summary.py <events.json> [today_iso_date]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    today = date.fromisoformat(argv[2]) if len(argv) > 2 else date.today()
    events = _load_events(path)
    print(summarize(events, today), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
