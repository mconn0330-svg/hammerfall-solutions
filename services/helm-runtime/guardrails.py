"""
guardrails.py — Runtime cost + rate guardrails (T0.A11).

Three layers, each provider-aware. T2.3's provider chain wires each one
to the correct call sites; this module lands the library + tests + the
factory that builds them from env vars.

  Layer 1 — RateAlarm              always on, provider-agnostic
  Layer 2 — ProMaxBudgetTracker    engaged only when claude-sdk provider runs
  Layer 3 — DollarCap              engaged only when anthropic-api provider runs

Every threshold is user-overridable via env var. Setting a threshold to `0`
disables it entirely (rate / Pro Max / dollar cap each opt-out independently).
A guardrail trip raises a structured exception; the FastAPI route returns a
429-style response per spec, runtime keeps serving other agents.

Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A11
Runbook: docs/runbooks/0003-guardrail-tripped.md
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict, deque
from datetime import UTC, date, datetime

from observability import get_logger

logger = get_logger("helm.guardrails")


# ─── Exceptions ───────────────────────────────────────────────────────────────


class GuardrailExceeded(Exception):
    """Base class for all guardrail trips. Catch this at the request boundary
    to return a uniform 429-style response regardless of which layer fired."""


class RateAlarmExceeded(GuardrailExceeded):
    """LLM call rate exceeded the configured per-minute or per-hour threshold."""


class ProMaxWeeklyExceeded(GuardrailExceeded):
    """Cumulative Pro Max token consumption this week exceeded 95% of budget."""


class DollarCapExceeded(GuardrailExceeded):
    """Today's anthropic-api spend would exceed the daily cap if this call ran."""


# ─── Layer 1: Rate alarm — always on, provider-agnostic ──────────────────────


class RateAlarm:
    """Tracks LLM calls per-minute and per-hour across all providers.

    Catches bug-shaped events (loops, accidental fan-out) at zero dollar cost.
    Sliding window via timestamp deque, trimmed lazily on each check.

    Setting any threshold to 0 disables that threshold check; setting all four
    to 0 makes the alarm a no-op recorder. 'Disabled' is correct for tests
    that don't care about rate, NOT for production — leaving an agent
    unbounded against its own loop is how budget incidents happen.
    """

    def __init__(
        self,
        calls_per_min_warn: int = 30,
        calls_per_min_block: int = 60,
        calls_per_hour_warn: int = 600,
        calls_per_hour_block: int = 1500,
    ) -> None:
        self.calls_per_min_warn = calls_per_min_warn
        self.calls_per_min_block = calls_per_min_block
        self.calls_per_hour_warn = calls_per_hour_warn
        self.calls_per_hour_block = calls_per_hour_block
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def check_and_record(self, agent: str, provider: str) -> None:
        """Record a new call and check both windows. Raises RateAlarmExceeded
        on block; emits structlog warning on warn; otherwise silent."""
        now = time.time()
        async with self._lock:
            # Trim entries older than 1 hour from the back.
            while self._calls and self._calls[0] < now - 3600:
                self._calls.popleft()

            calls_last_min = sum(1 for t in self._calls if t > now - 60)
            calls_last_hour = len(self._calls)

            if (self.calls_per_min_block > 0 and calls_last_min >= self.calls_per_min_block) or (
                self.calls_per_hour_block > 0 and calls_last_hour >= self.calls_per_hour_block
            ):
                logger.critical(
                    "rate.blocked",
                    agent=agent,
                    provider=provider,
                    last_min=calls_last_min,
                    last_hour=calls_last_hour,
                )
                raise RateAlarmExceeded(
                    f"Rate block: {calls_last_min} calls/min, {calls_last_hour} calls/hour"
                )

            if (self.calls_per_min_warn > 0 and calls_last_min >= self.calls_per_min_warn) or (
                self.calls_per_hour_warn > 0 and calls_last_hour >= self.calls_per_hour_warn
            ):
                logger.warning(
                    "rate.warn",
                    agent=agent,
                    provider=provider,
                    last_min=calls_last_min,
                    last_hour=calls_last_hour,
                )

            self._calls.append(now)


# ─── Layer 2: Pro Max weekly budget tracker — claude-sdk only ────────────────


class ProMaxBudgetTracker:
    """Approximates cumulative Pro Max token consumption per ISO week.

    Pro Max has rolling 5-hour and weekly limits set by Anthropic. We can't
    see those directly; we count tokens in/out via the SDK responses and
    warn at 70%, block at 95% of a configured weekly budget. Tuned via
    HELM_PROMAX_WEEKLY_BUDGET as observed throttle behavior dictates.

    `weekly_token_budget = 0` disables the tracker.
    """

    WARN_PCT: float = 0.70
    BLOCK_PCT: float = 0.95

    def __init__(self, weekly_token_budget: int = 5_000_000) -> None:
        self.weekly_token_budget = weekly_token_budget
        self._tokens_by_week: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def check_and_record(self, input_tokens: int, output_tokens: int) -> None:
        if self.weekly_token_budget == 0:
            return
        week_key = datetime.now(UTC).strftime("%Y-W%V")
        total = input_tokens + output_tokens
        async with self._lock:
            spent = self._tokens_by_week[week_key]
            projected = spent + total
            pct = projected / self.weekly_token_budget

            if pct >= self.BLOCK_PCT:
                logger.critical(
                    "promax.weekly_blocked",
                    spent=spent,
                    budget=self.weekly_token_budget,
                    pct=pct,
                )
                raise ProMaxWeeklyExceeded(
                    "Pro Max weekly budget at 95% — backing off to protect Claude.ai access"
                )

            if pct >= self.WARN_PCT:
                logger.warning(
                    "promax.weekly_warn",
                    spent=spent,
                    budget=self.weekly_token_budget,
                    pct=pct,
                )

            self._tokens_by_week[week_key] += total


# ─── Layer 3: Dollar cap — anthropic-api only ────────────────────────────────


class DollarCap:
    """Tracks daily Anthropic API spend and blocks calls that would exceed
    the cap. Engaged only when an agent slot routes to `anthropic-api`.

    `daily_cap_usd = 0` disables the cap (use case: Render deploy with
    pre-paid funds where rate-alarm is sufficient).

    Pricing constants below are pinned in code intentionally — changes to
    Anthropic pricing should land as a deliberate PR, not silently via
    config. T2.3 verifies these against the current published rates as part
    of provider-chain work.
    """

    # Anthropic API pricing (USD per token).
    # Source: https://www.anthropic.com/pricing — verify at T2.3.
    PRICING: dict[str, dict[str, float]] = {
        "claude-opus-4-7": {
            "input": 15.00 / 1_000_000,
            "output": 75.00 / 1_000_000,
        },
        "claude-sonnet-4-6": {
            "input": 3.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
        },
    }

    def __init__(self, daily_cap_usd: float = 5.0) -> None:
        self.daily_cap_usd = daily_cap_usd
        self._spend_by_day: dict[date, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def check_and_record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        if self.daily_cap_usd == 0:
            return
        price = self.PRICING.get(model)
        if not price:
            logger.warning("dollar_cap.unknown_model", model=model)
            return

        cost = price["input"] * input_tokens + price["output"] * output_tokens
        today = date.today()
        async with self._lock:
            if self._spend_by_day[today] + cost > self.daily_cap_usd:
                logger.critical(
                    "cost.cap_exceeded",
                    spent=self._spend_by_day[today],
                    cap=self.daily_cap_usd,
                    blocked_cost=cost,
                )
                raise DollarCapExceeded(f"Daily API cap ${self.daily_cap_usd} would be exceeded")
            self._spend_by_day[today] += cost
            logger.info(
                "cost.recorded",
                model=model,
                cost=cost,
                day_total=self._spend_by_day[today],
            )


# ─── Factory — build the three guardrails from env vars at startup ───────────


def from_env() -> tuple[RateAlarm, ProMaxBudgetTracker, DollarCap]:
    """Build the three guardrails using env-var overrides where present.
    Called once at service startup; instances live for the process lifetime.

    Env vars (all optional; defaults match spec):
        HELM_RATE_WARN_PER_MIN, HELM_RATE_BLOCK_PER_MIN
        HELM_RATE_WARN_PER_HOUR, HELM_RATE_BLOCK_PER_HOUR
        HELM_PROMAX_WEEKLY_BUDGET
        HELM_DAILY_COST_CAP_USD
    """
    rate = RateAlarm(
        calls_per_min_warn=int(os.environ.get("HELM_RATE_WARN_PER_MIN", "30")),
        calls_per_min_block=int(os.environ.get("HELM_RATE_BLOCK_PER_MIN", "60")),
        calls_per_hour_warn=int(os.environ.get("HELM_RATE_WARN_PER_HOUR", "600")),
        calls_per_hour_block=int(os.environ.get("HELM_RATE_BLOCK_PER_HOUR", "1500")),
    )
    promax = ProMaxBudgetTracker(
        weekly_token_budget=int(os.environ.get("HELM_PROMAX_WEEKLY_BUDGET", "5000000")),
    )
    cap = DollarCap(
        daily_cap_usd=float(os.environ.get("HELM_DAILY_COST_CAP_USD", "5.0")),
    )
    return rate, promax, cap
