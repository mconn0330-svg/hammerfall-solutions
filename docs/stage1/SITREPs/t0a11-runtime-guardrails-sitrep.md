# SITREP — T0.A11 Runtime Guardrails

**Date:** 2026-04-25
**Branch:** `feature/t0a11-runtime-guardrails`
**Tier:** STOP
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A11 (lines 733–884)

## Scope executed

Three guardrail classes + factory + tests + runbook. Per spec, the actual per-provider integration ("every provider call wrapped in `rate_alarm.check_and_record`...") happens in T2.3's provider chain — this PR lands the library, the env-var contract, and the operational doc so T2.3 has a stable surface to wire to.

| Layer | Class                 | Trigger                                 | Default thresholds                                    |
| ----- | --------------------- | --------------------------------------- | ----------------------------------------------------- |
| 1     | `RateAlarm`           | always on, provider-agnostic            | warn 30/min, block 60/min, warn 600/hr, block 1500/hr |
| 2     | `ProMaxBudgetTracker` | only when `claude-sdk` provider runs    | warn 70%, block 95% of 5M tokens/week                 |
| 3     | `DollarCap`           | only when `anthropic-api` provider runs | $5.00/day; pinned pricing for opus-4-7 + sonnet-4-6   |

All three engage independently; all thresholds env-overridable; setting any threshold to `0` disables that check.

## Files added

| File                                             | Purpose                                                                                                                      |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `services/helm-runtime/guardrails.py`            | NEW — 3 classes, 4 exception types (`GuardrailExceeded` base + one per layer), `from_env()` factory. ~250 lines.             |
| `services/helm-runtime/tests/test_guardrails.py` | NEW — 18 tests. Warn/block thresholds, sliding-window expiry, week-key rollover, unknown-model handling, env-factory wiring. |
| `docs/runbooks/0003-guardrail-tripped.md`        | NEW — third runbook in the repo. Covers all three trip types + diagnosis + fix paths.                                        |

## Verification

- `mypy --strict .` (helm-runtime) → 0 errors across 18 source files (guardrails + tests added)
- `ruff check .` + `black --check .` → clean (auto-fixed 1 ruff issue, applied black to 2 files during local iteration)
- `python -m pytest tests/test_guardrails.py -v` → **18 passed**
- Full suite still green except the same Py3.14 pydantic-wheels gap (`test_main_module_imports`) that's existed since T0.A3

## Implementation notes

1. **`GuardrailExceeded` is a new base class** that all three trip exceptions inherit from. Spec listed three peer exceptions (`RateAlarmExceeded`, `ProMaxWeeklyExceeded`, `DollarCapExceeded`); I added the base so the request-boundary handler in main.py (T2.3 will wire this) can catch one type for uniform 429-style responses regardless of which layer fired. Tests assert the inheritance chain.

2. **`datetime.now(UTC)` instead of `datetime.utcnow()`.** The spec snippet uses `utcnow()` which is deprecated in Python 3.12+. `now(UTC)` is the current idiom; identical semantics.

3. **All thresholds gracefully `0`-disable.** Spec table says "Set to 0 — disabled" but the original code didn't actually check for it. Added explicit zero-checks in each layer's threshold comparisons. Tests cover the disabled paths.

4. **`from_env()` factory** — spec didn't specify how the env vars get wired into instances; added a single factory function so the eventual T2.3 wiring is one line: `rate, promax, cap = from_env()` at startup. Reads all six env vars with the spec's exact names + defaults.

5. **Runbook numbered `0003`, not spec's `0008`.** Spec said "Runbook 0008 documents how to read each guardrail's logs." Sequential numbering in the repo (0001 = auth, 0002 = backup-restore, 0003 = guardrails) is the actual convention; "0008" was illustrative. Spec deviation flagged here.

6. **Pricing constants pinned in code with a "verify at T2.3" comment.** Spec said to verify against current Anthropic rates at implementation time; T2.3 owns provider-chain work and is the right place for the pricing-cycle sanity check.

## Spec deviations (small, flagged)

1. **No integration into the request boundary in this PR.** Spec says guardrail trips emit SSE `system_health` events and return 429 from the route. The route doesn't wrap LLM calls yet (no provider chain at T1; that's T2.3). T0.A11 lands the library and contract; T2.3 wires it. SITREP here makes the deferral explicit.

2. **Runbook number `0003` instead of `0008`** (see implementation note 5).

3. **`time.time()` is monkeypatched in tests, not `freezegun`-style.** No new dependency; pytest's `monkeypatch.setattr` does the job for the sliding-window tests.

## Adjacent debt explicitly NOT in scope

- **Integration into route handlers.** T2.3 (provider chain) wires `rate_alarm.check_and_record` into every provider call site. Documented in the file's docstring and the runbook.
- **SSE `system_health` event emission.** Same — depends on T2.3's response shape.
- **Persistent state across restarts.** Rate window and Pro Max counter live in memory; restart resets them. Acceptable for single-process runtime at T1; multi-instance Render deploys (Stage 2) need shared state (Redis or a Supabase counter).
- **Tuning thresholds against real usage.** Defaults are spec values. T1 close (T4.5) is the right time to revise based on observed usage.

## What this unlocks

- **T2.3 (provider chain)** has a stable guardrail surface to wire — `from_env()` returns the three instances; each provider call wraps `rate_alarm.check_and_record(agent, provider)` first, plus its layer-specific tracker on response.
- **Bug-shaped catastrophes are bounded.** Once T2.3 wires this, an agent loop hits the rate alarm at zero dollar cost rather than burning through Pro Max or anthropic-api budget.
- **Operational confidence.** Runbook 0003 means a real incident has a documented path: "which event name? identify the agent? raise the threshold or kill the loop?"
- **Phase 0A close is in sight.** Task 11 of ~15. Remaining: T0.A12 (ARCH — CI container build), T0.A13 (Batch — gitleaks), T0.A14 (ARCH — dependency automation), T0.A15 (Batch — cost summary). Two ARCH tasks have approved one-pagers; the Batch ones are short.

## STOP gate

Standing by for your explicit approval. After merge, T0.A12 (CI container build + GHCR publish) is next — ARCH-tier with an existing approved arch-note.
