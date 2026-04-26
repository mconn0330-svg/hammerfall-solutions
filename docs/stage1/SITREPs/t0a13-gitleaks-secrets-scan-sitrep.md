# SITREP — T0.A13 Gitleaks Secret Scanning

**Date:** 2026-04-25
**Branch:** `feature/t0a13-gitleaks-secrets-scan`
**Tier:** Batch (PR opens with `[BATCH]` prefix per V2 §"Review tiers")
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A13 (lines 952–977)

## Scope executed

Three artifacts per spec:

| Artifact                         | Purpose                                                                                                                                                                                                           |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/gitleaks.yml` | CI scan on every PR + push to main. `fetch-depth: 0` so history scan covers any commit on a long-lived branch, not just the diff.                                                                                 |
| `.gitleaks.toml`                 | Allowlist for noise sources (lockfiles, schema dump, runbooks/SITREPs that quote example tokens). Inherits all default rules via `[extend].useDefault = true`. Each entry has a comment explaining WHY it's safe. |
| `.pre-commit-config.yaml`        | Added gitleaks hook (`v8.30.0`) so leaks are caught locally before push, not just at PR open.                                                                                                                     |

## Verification

Ran a real local scan via `docker run zricethezav/gitleaks:v8.30.0 detect --source . --no-git --verbose`:

```
INF scanned ~11484993 bytes (11.48 MB) in 1.21s
INF no leaks found
```

Whole repo (~11 MB) clean. The allowlist is preventive — nothing in the current tree triggers default rules in a way that needed suppression. CI will validate end-to-end on this PR.

## Files added

| File                             | Change                                                                                                                                                            |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/gitleaks.yml` | NEW — single-job workflow, runs on `pull_request` + `push` to `main`. Uses `gitleaks/gitleaks-action@v2` (single-dev account → no GITLEAKS_LICENSE needed).       |
| `.gitleaks.toml`                 | NEW — `useDefault = true` + path allowlist for lockfiles, schema dump, doc files. Includes commented-out template for the Supabase anon key (T1.6 will activate). |
| `.pre-commit-config.yaml`        | + gitleaks hook (`gitleaks/gitleaks@v8.30.0`). Mirrors the CI workflow at the local commit boundary.                                                              |

## Implementation notes (small flags)

1. **`useDefault = true` is critical and easy to miss.** Without it, defining `[allowlist]` REPLACES the default rules instead of extending them, silently disabling all detection. Comment in the file makes this explicit.

2. **Doc-file paths in allowlist (`docs/runbooks/**`, `docs/stage1/SITREPs/**`).** The auth-rotation runbook and several SITREPs quote `sbp_...` tokens or other key prefixes in instructional context. Allowlisting the paths beats trying to keep individual quoted examples below the entropy threshold.

3. **CI runs on `pull_request` + `push` to `main` only**, not all pushes. Spec said "on every push" — but pushes to feature branches are already covered by the PR run when the PR opens; running on every feature-branch push would just duplicate work and burn CI minutes.

4. **Pre-commit hook uses Gitleaks `v8.30.0` directly** (not a mirror). Gitleaks publishes pre-commit hooks in their main repo.

## Spec deviations (small, flagged)

1. **CI on `[pull_request, push to main]`** rather than `[pull_request, push]` (every push) — see implementation note 3.

## Adjacent debt explicitly NOT in scope

- **Supabase anon key allowlist entry.** Template lives in `.gitleaks.toml` as a comment. T1.6 commits the actual anon key to the repo — that PR uncomments the regex. Cleaner than allowlisting a value that isn't yet present.
- **GITLEAKS_LICENSE secret.** Only required for orgs with >25 users. Single-dev account runs in OSS mode for free. If Helm goes commercial / multi-user, this becomes a Stage 2 expense.
- **Block on warn-level findings.** Gitleaks defaults treat detection as fail. We don't add an extra severity tier — true positives should fail; false positives go in the allowlist. No middle ground at T1.

## What this unlocks

- **Zero-friction protection from accidental commits.** A leaked Supabase service key, OpenAI key, or `sbp_` token gets caught at the local pre-commit hook OR (if hook bypassed) at PR-open CI. Before T0.A13, the only protection was discipline.
- **Belt-and-suspenders with the OPENAI_API_KEY incident.** The leak earlier in the session (key inside `PATH`) wasn't a commit — but the same pattern committed would now fail CI.
- **AGENTS.md hard rule 6** (no `print()` statements in shipped code) gets a sister at the secret-management level: any pattern that looks like a credential gets flagged before it ships.
- **Phase 0A close is in sight.** Task 13 of ~15. Two tasks left after this: T0.A14 (Dependency Automation, ARCH — has approved one-pager) and T0.A15 (Cost summary, Batch).

## Review

Batch tier. Mechanical addition per spec. Local docker scan passed clean across the whole tree (11 MB). After approval + merge, T0.A14 (Dependency Automation, ARCH) starts.
