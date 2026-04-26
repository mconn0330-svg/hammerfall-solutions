"""Tests for runtime guardrails (T0.A11).

Three classes, three exception types, one factory. Tests exercise:
  - warn vs block thresholds (RateAlarm: per-min + per-hour)
  - sliding-window expiry (RateAlarm)
  - week-key rollover (ProMaxBudgetTracker)
  - daily rollover + unknown-model handling + disabled mode (DollarCap)
  - env-var factory wiring (from_env)

`time.time` is monkeypatched to make sliding-window behavior deterministic.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from guardrails import (
    DollarCap,
    DollarCapExceeded,
    GuardrailExceeded,
    ProMaxBudgetTracker,
    ProMaxWeeklyExceeded,
    RateAlarm,
    RateAlarmExceeded,
    from_env,
)

# ─── Test helpers ─────────────────────────────────────────────────────────────


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Returns a setter that controls what `time.time()` returns inside
    guardrails.py. Initial value is 1_000_000_000 (an arbitrary epoch
    second; far enough from 0 to avoid degenerate sliding windows)."""
    state = {"now": 1_000_000_000.0}

    def fake_time() -> float:
        return state["now"]

    monkeypatch.setattr("guardrails.time.time", fake_time)

    def setter(new_now: float) -> None:
        state["now"] = new_now

    return setter


# ─── RateAlarm ────────────────────────────────────────────────────────────────


async def test_rate_alarm_passes_under_threshold(fake_clock: Callable[[float], None]) -> None:
    alarm = RateAlarm(calls_per_min_warn=10, calls_per_min_block=20)
    for _ in range(5):
        await alarm.check_and_record("agent_x", "local")
    # No raise.


async def test_rate_alarm_blocks_at_per_minute_block(fake_clock: Callable[[float], None]) -> None:
    alarm = RateAlarm(calls_per_min_warn=10, calls_per_min_block=3, calls_per_hour_block=0)
    await alarm.check_and_record("a", "p")
    await alarm.check_and_record("a", "p")
    await alarm.check_and_record("a", "p")  # third call brings count to 3 → block on next
    with pytest.raises(RateAlarmExceeded):
        await alarm.check_and_record("a", "p")


async def test_rate_alarm_blocks_at_per_hour_block(fake_clock: Callable[[float], None]) -> None:
    """Per-hour block fires even if per-minute is fine (calls spread over time)."""
    alarm = RateAlarm(
        calls_per_min_warn=0,
        calls_per_min_block=0,  # disabled
        calls_per_hour_warn=0,
        calls_per_hour_block=2,
    )
    fake_clock(2_000_000.0)
    await alarm.check_and_record("a", "p")
    fake_clock(2_001_000.0)  # ~17 min later
    await alarm.check_and_record("a", "p")
    fake_clock(2_002_000.0)
    with pytest.raises(RateAlarmExceeded):
        await alarm.check_and_record("a", "p")


async def test_rate_alarm_zero_block_disables_check(fake_clock: Callable[[float], None]) -> None:
    """All-zero thresholds make the alarm a no-op recorder. Tests use this
    to exercise other behaviors without spurious blocks."""
    alarm = RateAlarm(
        calls_per_min_warn=0, calls_per_min_block=0, calls_per_hour_warn=0, calls_per_hour_block=0
    )
    for _ in range(100):
        await alarm.check_and_record("a", "p")
    # No raise.


async def test_rate_alarm_window_expires(fake_clock: Callable[[float], None]) -> None:
    """Calls older than 1 hour drop out of the window and stop counting."""
    alarm = RateAlarm(calls_per_min_warn=0, calls_per_min_block=0, calls_per_hour_block=3)
    fake_clock(3_000_000.0)
    await alarm.check_and_record("a", "p")
    await alarm.check_and_record("a", "p")
    # Jump 2 hours forward; the prior calls are now outside the window.
    fake_clock(3_000_000.0 + 7200)
    for _ in range(2):
        await alarm.check_and_record("a", "p")
    # No raise — the window only sees the 2 new calls.


async def test_rate_alarm_exception_inherits_from_base(fake_clock: Callable[[float], None]) -> None:
    """Callers can catch GuardrailExceeded for uniform 429 handling."""
    alarm = RateAlarm(calls_per_min_block=1)
    await alarm.check_and_record("a", "p")
    with pytest.raises(GuardrailExceeded):
        await alarm.check_and_record("a", "p")


# ─── ProMaxBudgetTracker ──────────────────────────────────────────────────────


async def test_promax_passes_under_warn() -> None:
    tracker = ProMaxBudgetTracker(weekly_token_budget=1000)
    await tracker.check_and_record(input_tokens=100, output_tokens=200)
    # 30% of budget; no raise, no warn.


async def test_promax_warns_at_70_pct() -> None:
    """Warn fires but the call still records."""
    tracker = ProMaxBudgetTracker(weekly_token_budget=1000)
    await tracker.check_and_record(input_tokens=400, output_tokens=300)  # 70% projected
    # No raise (warn only).


async def test_promax_blocks_at_95_pct() -> None:
    tracker = ProMaxBudgetTracker(weekly_token_budget=1000)
    await tracker.check_and_record(input_tokens=500, output_tokens=400)  # 90%, no block
    with pytest.raises(ProMaxWeeklyExceeded):
        await tracker.check_and_record(input_tokens=50, output_tokens=10)  # would push to 96%


async def test_promax_zero_budget_disables() -> None:
    """weekly_token_budget=0 makes the tracker a no-op."""
    tracker = ProMaxBudgetTracker(weekly_token_budget=0)
    for _ in range(100):
        await tracker.check_and_record(input_tokens=10_000_000, output_tokens=10_000_000)
    # No raise.


# ─── DollarCap ────────────────────────────────────────────────────────────────


async def test_dollar_cap_passes_under_threshold() -> None:
    cap = DollarCap(daily_cap_usd=5.0)
    # claude-sonnet-4-6 input price = $3 / 1M tokens.
    # 1000 input tokens = $0.003 — well under cap.
    await cap.check_and_record("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)


async def test_dollar_cap_blocks_when_call_would_exceed() -> None:
    cap = DollarCap(daily_cap_usd=0.10)
    # claude-opus-4-7 output price = $75/M; 2000 output tokens = $0.15 — exceeds.
    with pytest.raises(DollarCapExceeded):
        await cap.check_and_record("claude-opus-4-7", input_tokens=0, output_tokens=2000)


async def test_dollar_cap_unknown_model_records_warning_not_block() -> None:
    """Unknown models log a warning and pass through — better than silently
    dropping the call. T2.3 surfaces unknown-model alerts in routine review."""
    cap = DollarCap(daily_cap_usd=0.01)  # tiny cap
    # Unknown model — would block on real pricing but we have none, so passes.
    await cap.check_and_record("claude-haiku-future", input_tokens=999_999, output_tokens=999_999)


async def test_dollar_cap_zero_disables() -> None:
    cap = DollarCap(daily_cap_usd=0.0)
    # Even astronomically expensive call passes.
    await cap.check_and_record("claude-opus-4-7", input_tokens=10_000_000, output_tokens=10_000_000)


async def test_dollar_cap_exception_inherits_from_base() -> None:
    cap = DollarCap(daily_cap_usd=0.01)
    with pytest.raises(GuardrailExceeded):
        await cap.check_and_record("claude-opus-4-7", input_tokens=0, output_tokens=10_000)


# ─── from_env factory ─────────────────────────────────────────────────────────


def test_from_env_uses_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "HELM_RATE_WARN_PER_MIN",
        "HELM_RATE_BLOCK_PER_MIN",
        "HELM_RATE_WARN_PER_HOUR",
        "HELM_RATE_BLOCK_PER_HOUR",
        "HELM_PROMAX_WEEKLY_BUDGET",
        "HELM_DAILY_COST_CAP_USD",
    ):
        monkeypatch.delenv(var, raising=False)

    rate, promax, cap = from_env()
    assert rate.calls_per_min_warn == 30
    assert rate.calls_per_min_block == 60
    assert rate.calls_per_hour_warn == 600
    assert rate.calls_per_hour_block == 1500
    assert promax.weekly_token_budget == 5_000_000
    assert cap.daily_cap_usd == 5.0


def test_from_env_overrides_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELM_RATE_BLOCK_PER_MIN", "120")
    monkeypatch.setenv("HELM_PROMAX_WEEKLY_BUDGET", "10000000")
    monkeypatch.setenv("HELM_DAILY_COST_CAP_USD", "25.00")

    rate, promax, cap = from_env()
    assert rate.calls_per_min_block == 120
    assert promax.weekly_token_budget == 10_000_000
    assert cap.daily_cap_usd == 25.0


def test_from_env_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting any threshold to "0" disables that check at the dependency
    level — confirming the env interface honors the spec's user-overridable
    contract."""
    monkeypatch.setenv("HELM_DAILY_COST_CAP_USD", "0")
    monkeypatch.setenv("HELM_PROMAX_WEEKLY_BUDGET", "0")

    _, promax, cap = from_env()
    assert cap.daily_cap_usd == 0.0
    assert promax.weekly_token_budget == 0
