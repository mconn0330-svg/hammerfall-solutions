# SITREP — T0.A14 Dependency Automation

**Date:** 2026-04-25
**Branch:** `feature/t0a14-dependency-automation`
**Tier:** STOP
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A14 (lines 980–1023)

## Scope executed

One artifact: `.github/dependabot.yml`. Four ecosystems, weekly Monday cadence, grouped to keep PR volume sane, capped at 5 open PRs per ecosystem.

| Ecosystem        | Path                     | Grouping                           | Notes                                                                       |
| ---------------- | ------------------------ | ---------------------------------- | --------------------------------------------------------------------------- |
| `pip`            | `/services/helm-runtime` | prod / dev                         | Updates requirements.txt directly (pip-compile interaction — see gap below) |
| `npm`            | `/helm-ui`               | prod / dev (via `dependency-type`) | Lockfile-aware; clean fit                                                   |
| `github-actions` | `/`                      | (ungrouped)                        | One PR per action bump; small surface                                       |
| `docker`         | `/services/helm-runtime` | (ungrouped)                        | Reads `FROM` lines in Dockerfile (ARG-indirection gap — see below)          |

Auto-merge: NOT shipped (per spec — "T0.A14 ships the config but auto-merge is opt-in").

## Files added

| File                     | Change                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| `.github/dependabot.yml` | NEW — 4 ecosystems per spec, with one prod-group exclude tweak (see implementation note 1). |

## Implementation notes (small flags)

1. **Expanded the prod-group `exclude-patterns`.** Spec listed `pytest*, mypy*, ruff*, pre-commit*`. I added `black*`, `pip-tools*`, `types-*` because they're all dev deps in our actual `requirements-dev.in`. Removed `pre-commit*` because pre-commit isn't in our requirements at all (it's installed via `pip install --user pre-commit` per T0.A2). Spec was illustrative; reality is what's in the lockfile.

2. **No auto-merge workflow.** Per spec "Maxwell decides at PR time." If auto-merge becomes desired (e.g., dev-only patch bumps that always pass CI), add a separate workflow gated on a repo variable. Cleaner to add the trigger when there's a real pattern than to ship dormant code.

3. **Verified `dependabot.yml` schema** by checking against the GitHub-hosted JSON schema (`schemastore.org/dependabot-2.0.json`) before commit. Pre-commit's `check-yaml` validates well-formedness, not Dependabot semantics.

## Known gaps (will surface on first Monday run)

These are real interactions between Dependabot and our existing tooling that I don't have a clean fix for in this PR. Documenting so the first runs aren't surprises:

### Gap 1: pip + pip-compile

**Setup:** Our T0.A7 workflow generates `requirements.txt` from `requirements.in` via `pip-compile --generate-hashes --strip-extras` inside `python:3.12.4-slim-bookworm`. CI runs a sync check that re-generates and `git diff --exit-code`s.

**Dependabot behavior:** Dependabot's pip ecosystem updates `requirements.txt` directly. It has its own resolver and picks transitive deps independently of pip-compile.

**Probable failure mode:** Dependabot's PR bumps a package and its hashes; CI sync check regenerates from `requirements.in`, picks different transitives or hash ordering, `git diff --exit-code` fails. Dependabot PRs all fail CI on the lockfile sync step.

**Two paths if this becomes noisy:**

- **Add a regenerate-on-Dependabot-PR workflow** — on `pull_request` from `dependabot[bot]`, run pip-compile and force-push the regenerated lockfile to the PR branch. ~30 lines of yaml.
- **Switch to Renovate** — has explicit `pip-compile` workflow detection. Larger config change but the "right" tool for this setup.

I'm not pre-fixing because the gap might not be as severe as I think (Dependabot may resolve to the same versions pip-compile would, in which case the sync check passes). First Monday tells us.

### Gap 2: docker ecosystem + ARG-based FROM line

**Setup:** Our Dockerfile uses:

```dockerfile
ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
```

**Dependabot behavior:** Dependabot's docker ecosystem looks for literal versions in `FROM` lines. ARG indirection may bypass the parser; in that case, base-image bumps don't get auto-PRed and we'd track Python version manually.

**If confirmed bad:** the fix is small — flip the Dockerfile to a literal `FROM python:3.12.4-slim-bookworm AS builder` and lose the ARG. Cosmetic; ARG was never load-bearing.

## Spec deviations (small, flagged)

1. **`exclude-patterns` differs from spec example** (see implementation note 1). Spec was illustrative; reality is the actual lockfile.

## Adjacent debt explicitly NOT in scope

- **Renovate migration.** Spec preferred Dependabot for T1 simplicity; Renovate is the upgrade path if Dependabot+pip-compile becomes painful. Stage 2 work either way.
- **Auto-merge workflow.** Per spec — opt-in, not auto-installed.
- **Cron-driven `pip-compile --upgrade`.** Alternative to Dependabot's pip ecosystem. Not needed unless Dependabot's pip behavior is too noisy to live with.

## What this unlocks

- **Pinned deps stay current without manual tracking.** Monday morning, up to 20 PRs across the four ecosystems land in your queue. You skim, merge what looks safe, close what doesn't.
- **CVE response time drops to "next Monday."** Without Dependabot, knowing which package needs a security bump requires manual scans. With it, the bump shows up automatically.
- **Lockfile drift is visible.** If Dependabot's pip PRs consistently fail the sync check (Gap 1), that's the signal to add the regenerate-on-PR workflow OR switch to Renovate.
- **Final Phase 0A task ahead.** T0.A14 = task 14 of ~15. T0.A15 (Cost summary, Batch) closes Phase 0A.

## STOP gate

Standing by for your explicit approval.

Two things to keep an eye on first Monday after merge:

1. How many Dependabot PRs land
2. Whether the pip ones fail the lockfile sync check

If either is painful, follow-up PR addresses. If both behave fine, T0.A14 is durable.

After approval + merge, T0.A15 (cost summary, Batch) closes Phase 0A.
