# SITREP — AGENTS.md "Clean Adjacent Debt as You Go" Rule

**Date:** 2026-04-25
**Branch:** `feature/agents-clean-as-you-go-rule`
**Tier:** STOP (operating-contract amendment per AGENTS.md maintenance footer)
**Spec:** N/A — direct Maxwell direction during T0.A3 PR review.

## Scope executed

Maxwell's direction (verbatim): _"I actually think we should change that... Accumulated tech debt is worse."_

Replaces the AGENTS.md "Don't gold-plate" soft rule with "Clean adjacent debt as you go." The new rule:

1. **Invites in-flight cleanup** of broken windows you encounter while editing — typos, dead vars, lint errors, stale comments, obsolete refs.
2. **Reframes the Findings queue** as a place for _non-adjacent_ discoveries only. "I noticed this while I was here" → fix in flight. "I'd have to go looking for this" → file a Finding.
3. **Preserves the scope-creep guard** by drawing the line at _features_: V2 is still the floor and ceiling for T1 features, just not for cleanup.

## Files changed

| File              | Change                                                                                                                                                                                             |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md`       | Replaces both soft-rule bullets in the "Don't balloon" / "Don't gold-plate" pair with the new pair: "Clean adjacent debt as you go" (positive direction) + reworded Findings rule (negative test). |
| `CONTRIBUTING.md` | Mirror update to the "When you find a problem" section, keeping the contract human-facing doc consistent.                                                                                          |

## Why this rule change matters

The old "don't gold-plate" rule was right in spirit (no scope explosion) but wrong in practice. Surfaced concretely during T0.A3 (PR #100):

- Discovered 349 pre-existing eslint errors in helm-ui/. Filed Finding #004, deferred to a future "I'll come back to it" PR. That deferral is exactly the failure mode Maxwell flagged: _the "I'll come back to it" PR rarely happens_.
- The eslint hook bug surfaced by T0.A3 ALSO surfaced because of a scope adjacency. Under the old rule, it could have been a Finding (debt). Instead it was fixed in flight. The PR was better for it.

The new rule names the test that already worked in practice: **adjacency**. Not "stay strictly inside your task" (too narrow, encourages debt) and not "fix everything you see" (too broad, encourages scope explosion). The line: was your hand already on this code? Then fix it. Were you about to go hunt for related dirt? Don't.

## Spec deviations

None. Operating contract changes don't have spec sections; they ARE the spec for "how we work."

## What this unlocks

- **Immediately:** the Finding #004 single-shot eslint cleanup PR (next) is now grounded in current policy, not "policy that's coming."
- **Going forward:** every PR-author (humans + agents) reads "if you noticed it because of work you're doing, just fix it." Less Findings queue churn, less debt accumulation, less "while I'm here" anxiety.
- **For T0.B / T1.x / T2.x onward:** the cleanup-in-flight default applies as the runtime and UI grow. Adjacent dead code, leftover comments from prior tasks, small tech debt around the edges — all expected to be fixed by whoever's there.

## Risk if wrong

The risk pattern under the new rule is _cleanup PRs that grow unbounded_ — someone touches App.jsx and decides to rewrite a third of helm-ui. The boundary clauses guard against this:

- "must be in code you're already editing or directly adjacent" → a 30-line touch doesn't authorize a 600-line refactor of the rest of the file
- "new features still go through Maxwell" → the line stays intact between cleanup and feature work

If a PR does balloon under the new rule, that's a feedback signal worth catching at review — but the bias is now toward fixing rather than deferring.

## STOP gate

Operating-contract amendment. Standing by for Maxwell's explicit approval before merge. After approval + merge, the Finding #004 single-shot eslint cleanup PR ships next.
