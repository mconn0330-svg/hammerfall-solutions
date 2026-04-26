#!/usr/bin/env python3
"""
T0.A15 — Fetch cost events from the configured log source.

This is the T1 placeholder. The runtime emits structured `cost.recorded`
events (T0.A11's DollarCap, wired by T2.3), but at T1 the runtime runs on
Maxwell's local host and CI on GitHub Actions can't reach it directly.

Three viable mechanisms when a log destination ships:
  1. HTTP fetch from a Render-deployed runtime (T4.11 onward)
  2. SSH + tail of local container logs (Tailscale tunnel)
  3. Direct read from a log aggregator (Loki / S3 / Supabase)

This script picks #1 (HTTP) as the long-term default since T4.11 will deploy
a runtime that exposes a structured-log endpoint. Until then, set
`HELM_COST_LOG_URL` to a real URL or accept the empty-result fallback.

Output: JSON array on stdout, suitable for `cost_summary.py`.

Usage:
    python3 scripts/fetch_cost_events.py [--days 7] [--source <url>]

Env:
    HELM_COST_LOG_URL  HTTP endpoint serving JSON-line `cost.recorded` events.
                       If unset, prints `[]` and exits 0 (graceful degrade so
                       the weekly workflow still produces a "no data" summary).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta


def fetch(source: str, days: int) -> list[dict[str, object]]:
    """Fetch the last `days` days of cost events from `source` (HTTP URL).
    Expected response: newline-delimited JSON, one event per line."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    url = f"{source}?since={cutoff}"

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(
            f"warning: fetch from {url} failed: {e}; returning empty", file=sys.stderr
        )
        return []

    events: list[dict[str, object]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip malformed lines; surfaces as "fewer events" not as crash.
            continue
    return events


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Days of history to fetch")
    parser.add_argument(
        "--source",
        default=os.environ.get("HELM_COST_LOG_URL", ""),
        help="HTTP URL serving JSONL cost events (default: $HELM_COST_LOG_URL)",
    )
    args = parser.parse_args(argv[1:])

    if not args.source:
        # T1 default state: no log destination configured. Empty array makes
        # cost_summary.py emit a "no events recorded" report — which is the
        # correct signal until T2.3 wires the provider chain.
        print(
            "warning: HELM_COST_LOG_URL unset and no --source given; emitting []",
            file=sys.stderr,
        )
        json.dump([], sys.stdout)
        return 0

    events = fetch(args.source, args.days)
    json.dump(events, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
