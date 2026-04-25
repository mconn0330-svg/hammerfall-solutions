# SITREP — T0.A4 CI Pipeline

**Date:** 2026-04-25
**Branch:** `feature/t0a4-ci-pipeline`
**Tier:** STOP (architect-tier impact — changes the merge workflow)
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A4 (lines 366–425)

## Scope executed

T0.A4 closes the Phase 0A "rules and enforcement" arc. T0.A1 wrote the rules. T0.A2 enforces them locally. T0.A3 gave CI something to run. T0.A4 wires the GitHub Actions workflow that runs all of it on every PR and push.

`.github/workflows/ci.yml` defines three parallel jobs. After Maxwell sets branch protection on `main` (post-merge step per spec), all three must be green before merge.

## Jobs

| Job                     | Steps                                                                                                                            |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `python` (helm-runtime) | checkout → setup-python 3.12 (with pip cache) → install requirements + dev → `ruff check .` → `black --check .` → `pytest --cov` |
| `ui` (helm-ui)          | checkout → setup-node 20 (with npm cache) → `npm ci` → `npm run lint` → `npm test -- --run` → `npm run build`                    |
| `commitlint`            | checkout (full history) → setup-node 20 → install commitlint → lint commits in PR range (or `HEAD~1..HEAD` on push)              |

## Spec deviations

**1. `mypy --strict` step deferred to T0.A5.** The spec yaml includes a Python type-check step (`mypy . --strict`). T0.A5 is the "Type Discipline (ADR-001)" task that introduces mypy and types every signature in the runtime. Adding the mypy step now would either:

- Leave CI red-by-design until T0.A5 lands (violates AGENTS.md hard rule 7 — "don't claim a PR is ready until CI is green")
- Force this PR to bundle T0.A5's full type pass (out of scope, undermines T0.A5's separate STOP-tier review)

The honest resolution: land the workflow without the mypy step. T0.A5's PR adds the step alongside the type pass, in one atomic green-CI change. A `# T0.A5` comment in `ci.yml` records the deferral.

**2. `black --check .` instead of `ruff format --check .`** The spec yaml uses `ruff format --check .` for format validation. T0.A2's pre-commit hooks installed `black` (not `ruff format`) as the formatter. Running `ruff format --check` in CI without first installing `ruff format` (or migrating local from black to ruff format) would cause local-vs-CI drift — a file that passes `black` locally might fail `ruff format --check` in CI on subtle differences.

The honest resolution: run `black --check .` to mirror the local toolchain exactly. Both tools produce black-style output; this is implementation detail, not behavior change. If we later migrate the formatter to `ruff format`, both pre-commit and CI should flip together.

**3. Commitlint step is more defensive than the spec excerpt.** The spec yaml shows `npx commitlint --from origin/main --to HEAD`. On a `pull_request` event the GitHub-Actions checkout doesn't fetch `origin/main` by default (even with `fetch-depth: 0`). Replaced with the explicit `pull_request.base.sha` / `head.sha` event-payload values, with a `push`-event fallback that lints `HEAD~1..HEAD`. Same intent, robust against checkout quirks.

## What this unlocks

- **AGENTS.md hard rule 7** ("don't claim a PR is ready until CI is green") becomes mechanical — every PR has a verifiable signal.
- **T0.A2 + T0.A3** become enforced on every contributor (humans + agents), not just the ones who installed pre-commit locally.
- **Post-merge action for Maxwell:** set branch protection on `main` requiring all three jobs to pass before merge. (The workflow can't enforce this itself; it has to be configured in GitHub repo settings.)
- **T0.A5 (Type Discipline)** is the natural next task. It adds mypy, types every signature, and re-enables the deferred mypy step in this same `ci.yml`.

Phase 0A pacing note: task 4 of ~15. With T0.A1–T0.A4 complete, the rules-and-enforcement arc closes. Subsequent Phase 0A tasks (T0.A5 type discipline → T0.A6 observability → T0.A7 deployment hardening → ...) build _on top of_ this foundation rather than alongside it.

## Verification plan

Once this PR is opened, the workflow runs on the PR itself. **All three jobs must be green before merge.** That's the smoke test for T0.A4: the PR validates its own infrastructure.

If a job goes red, the failure is the data — fix forward in this branch until green.

## Findings filed

None.

## STOP gate

Architect-tier impact. Standing by for Maxwell's explicit approval before merge. After approval + merge, two follow-ups:

1. Maxwell sets branch protection on `main` (GitHub repo settings → Branches → require status checks)
2. T0.A5 (Type Discipline + ADR-001) starts immediately
