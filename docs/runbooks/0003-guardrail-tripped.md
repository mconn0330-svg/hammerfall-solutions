# Runbook 0003 — Guardrail tripped (rate / Pro Max / dollar cap)

**Status:** Active
**Created:** 2026-04-25
**Last verified:** 2026-04-25 (initial — exercised via test suite, not a real prod incident)
**Owner:** Maxwell McConnell

## Symptom

A request to `/invoke/<agent>` returns 429 (or the runtime emits an SSE `system_health` event with `severity: "warning"`), and the agent's response includes one of:

- `"error": "rate_alarm_exceeded"` — too many LLM calls in the last minute or hour
- `"error": "promax_weekly_exceeded"` — Pro Max weekly token budget at 95%
- `"error": "dollar_cap_exceeded"` — today's anthropic-api spend would exceed the configured daily cap

Other agents continue to serve while a single agent is blocked. If multiple agents share the same provider, they all see the same trip.

## Diagnosis

Identify which guardrail tripped. Each layer logs to `helm.guardrails` with a distinct event name:

```bash
# Rate alarm
docker compose logs helm-runtime | grep -E '"event":"rate\.(blocked|warn)"'

# Pro Max weekly tracker
docker compose logs helm-runtime | grep -E '"event":"promax\.weekly_(blocked|warn)"'

# Dollar cap
docker compose logs helm-runtime | grep -E '"event":"cost\.(cap_exceeded|recorded)"'
```

Look for the agent name in the log line. A single agent monopolizing the rate alarm is almost always a loop bug. Multiple agents tripping over hours suggests legitimate load (and the threshold is too low for current usage).

## Fix

### If rate alarm tripped

**First, identify the agent.** The log line includes `agent=...`. If one agent dominates:

1. Check that agent's recent code changes — a loop, a fan-out, an accidental retry storm. Common culprits:
   - Contemplator's two-pass loop firing without proper exit
   - A handler retrying on a 5xx without backoff
   - Hot tab on the UI repeatedly invoking the same agent
2. Kill the loop:
   ```bash
   # If it's a runtime-side bug, restart cleans the in-memory rate window.
   docker compose restart helm-runtime
   ```
3. Once the loop is fixed, the rate window naturally clears in 60 minutes.

**If the agent is legitimate and the threshold is the problem,** raise it:

```bash
# Edit .env or your shell:
export HELM_RATE_BLOCK_PER_MIN=120  # was 60
docker compose restart helm-runtime
```

### If Pro Max weekly tracker tripped

This means the runtime estimates you've consumed 95% of your weekly Pro Max token budget. Two paths:

1. **You're nearing your real Pro Max limit.** Back off until the week rolls over (Monday UTC). The runtime is doing its job — it's protecting your access to Claude.ai for Maxwell-the-human.
2. **The estimate is wrong** (tokens-counted ≠ tokens-billed-by-Anthropic in subtle ways). Compare the runtime's estimate to your Anthropic account dashboard. If the estimate is materially higher than reality, raise the budget:
   ```bash
   export HELM_PROMAX_WEEKLY_BUDGET=10000000  # 2× the default
   docker compose restart helm-runtime
   ```
   Keep an eye on actual Anthropic usage for a week to validate the new value.

### If dollar cap tripped

Today's anthropic-api spend is at or near the configured daily limit.

1. **Check what burned the budget.** `cost.recorded` log lines have `model` + `cost` per call. Recent run-ups usually trace to one model + one agent.
2. **If the burn was a bug** (loop, runaway): restart, fix the loop, the cap auto-resets at midnight UTC.
3. **If the burn was legitimate and you want to keep going today,** raise the cap:
   ```bash
   export HELM_DAILY_COST_CAP_USD=25.00  # was 5.00
   docker compose restart helm-runtime
   ```
   Or set to `0` to disable entirely (only on Render with prepaid funds, never on local dev).

**Verification:** the agent that was getting 429s succeeds on the next invocation; `helm.guardrails` no longer emits `*.blocked` events.

## Root cause

T0.A11 introduced three guardrails because the threat model split into three:

- **Rate alarm** — bug-shaped catastrophe (loops, fan-out). Fires regardless of provider; zero dollar cost to be wrong about.
- **Pro Max tracker** — protects the _human's_ access to Claude.ai. Engaged only when `claude-sdk` is the active provider.
- **Dollar cap** — protects the _budget_ on paid-API providers. Engaged only when `anthropic-api` is the active provider.

Each layer is overridable. Default thresholds were chosen for "single-developer with Pro Max + local models" — adjust them as your usage profile changes.

- Related code: `services/helm-runtime/guardrails.py`
- Related ADRs: ADR-010 (provider abstraction — referenced in spec, lands at T2.3)
- Related findings: none

## Prevention

What reduces guardrail trips:

- **Don't write loops.** Every agent handler should have an explicit termination condition. Code review for new handlers includes "what stops this from calling itself forever?"
- **Test under load before deploying.** A handler that's fine for 1 user can blow the rate alarm at 10 — but at T1 there's only 1 user, so this is a Stage 2 concern.
- **Monitor the warn-level events.** `rate.warn` and `promax.weekly_warn` fire before the block. If you see them in the logs regularly, raise the threshold deliberately rather than waiting for the block.
- **Pricing drifts.** The `DollarCap.PRICING` constants are pinned. If Anthropic changes pricing and you don't update the constants, the cap calculation drifts. T2.3 verifies these as part of the provider-chain build.

What automates this further (Stage 2):

- Wire `helm.guardrails.rate.warn` events into a routine alert (Slack/PagerDuty equivalent) so warn-level signals don't get lost in log volume.
- Pull live pricing from Anthropic's API (when/if they expose one) so `DollarCap` doesn't drift on pricing changes.

---

_Maintenance: Re-verify this runbook after any change to `guardrails.py` (especially threshold defaults or pricing constants), or after first real production trip (the trip is the test). Update "Last verified" date when re-tested._
