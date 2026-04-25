# SITREP — T0.A2 Pre-commit Hooks

**Date:** 2026-04-25
**Branch:** `feature/t0a2-precommit-hooks`
**Tier:** Batch (PR opens with `[BATCH]` prefix per V2 §"Review tiers")
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A2 (line 86)

## Scope executed

T0.A2 lands the local enforcement layer for the contract T0.A1 froze. Five hooks
wired through the standard `pre-commit` framework: ruff + black (Python),
prettier + eslint (JS/TS), commitlint (commit-msg). The framework is
cross-language, language-agnostic, and the de-facto standard — chosen over
husky/lefthook because we have both Python and JS in the same repo and
pre-commit handles both natively.

## Files added

| File                                   | Purpose                                                                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `.pre-commit-config.yaml`              | Wires all 5 hooks + 6 generic safety nets (trailing-whitespace, end-of-file, merge-conflict, yaml/json validation, large-file guard). |
| `services/helm-runtime/pyproject.toml` | Ruff + black config: line-length 100, py311 target, ruff lint rules `E,F,I,B,UP`.                                                     |
| `.prettierrc`                          | Prettier config matching existing helm-ui style: `singleQuote: true`, `semi: false`, `printWidth: 100`, `trailingComma: 'es5'`.       |
| `.prettierignore`                      | Excludes build output, node_modules, memory snapshots, historical docs, lockfiles.                                                    |

## Pinned versions (post-autoupdate)

- `pre-commit-hooks` v6.0.0
- `ruff-pre-commit` v0.15.12
- `black-pre-commit-mirror` 26.3.1
- `mirrors-prettier` v4.0.0-alpha.8
- `commitlint-pre-commit-hook` v9.24.0
- commitlint runtime: `@commitlint/config-conventional@19`

Future bumps via `python -m pre_commit autoupdate`.

## Setup for collaborators (humans + agents)

```bash
pip install --user pre-commit
python -m pre_commit install --hook-type pre-commit --hook-type commit-msg
```

After install, hooks fire automatically on every `git commit`. To run on
already-staged files without committing: `python -m pre_commit run`. To run
across the whole repo (note: will reformat existing JS code that predates
prettier — see "Progressive coverage" below): `python -m pre_commit run --all-files`.

## Progressive coverage decision

Pre-commit only operates on **files staged in the current commit** by default.
Existing unstaged code (~all of helm-ui/) is _not_ reformatted by this PR.
Coverage grows as files are touched in future PRs. Rationale: a one-shot
`prettier --write` across helm-ui/ would touch every JSX file and produce a
massive churn diff that buries real changes. Better to absorb the format pass
incrementally as files are edited anyway.

The cost: someone running `pre-commit run --all-files` _will_ see prettier
reformat the world. That's expected; the hook config is correct, the
codebase just hasn't been swept yet. A scheduled sweep can land later as
its own `style:` PR if desired (Findings queue candidate).

## Spec deviations

None. The 5 hooks listed in V2 §T0.A2 are wired exactly. Generic safety-net
hooks (trailing-whitespace, etc.) added on top — standard pre-commit hygiene,
no spec conflict.

## Findings filed

- **Finding #003** — Repo lacks a root `.gitignore`. Surfaced by this PR's
  `git status` showing six untracked junk paths
  (`$TMPFILE`, `helm-ui/.vite/`, two `__pycache__/` dirs, `supabase/.temp/`,
  root `node_modules/.cache/`). Resolution deferred to a small standalone
  `chore(repo)` PR per the AGENTS.md "don't gold-plate" rule. See
  `docs/stage1/Post_T1_Findings.md`.

## Smoke test

```
$ python -m pre_commit run --files .pre-commit-config.yaml services/helm-runtime/pyproject.toml .prettierrc .prettierignore
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
check for merge conflicts................................................Passed
check yaml...............................................................Passed
check json...........................................(no files to check)Skipped
check for added large files..............................................Passed
ruff check...........................................(no files to check)Skipped
black................................................(no files to check)Skipped
prettier.................................................................Passed
eslint (helm-ui).....................................(no files to check)Skipped
```

Hooks that show "Skipped" had no matching files in this PR (no .py / .json /
.jsx). They will fire on future PRs that touch those file types.

The commit-msg hook (commitlint) is exercised by this PR's own commit message —
if you're reading a merged version, it passed.

## Local environment note

On Windows with Norton AV, real-time scanning of `%USERPROFILE%\.cache\pre-commit\`
will quarantine downloaded hook binaries (ruff.exe, black.exe, node bins) and
hang `pre-commit install`. Add an exclusion for that directory plus
`%LOCALAPPDATA%\pre-commit\` and the local `.git\hooks\` if hooks won't run.
This is a Windows + Norton specific issue; CI on Linux runners (T0.A4) is
not affected. Worth a runbook entry once T0.A4 lands and we're sure of the
exact path set.

## What this unlocks

- **T0.A1 → T0.A2**: the operating contract is now mechanically enforced. You
  can no longer commit a non-conforming message or land formatting drift.
- **T0.A4 (CI pipeline)** runs the same `pre-commit run --all-files` in
  GitHub Actions. The config is single-source-of-truth for both local and CI.
- **T0.A13 (gitleaks secrets scanning)** will land as another pre-commit repo
  in this same file — minimal incremental work because the framework is now
  in place.

Phase 0A pacing note: task 2 of ~15 infra tasks before product-visible change.
With T0.A1 + T0.A2 done, the rules are written _and_ enforced. Next infra
beat is T0.A3 (test harness) → T0.A4 (CI) which together close the
"green CI before claiming done" loop in `AGENTS.md` rule 7.

## Review

Batch tier — Maxwell reviews in groups, no STOP gate. After approval + merge,
T0.A3 (test harness) starts.
