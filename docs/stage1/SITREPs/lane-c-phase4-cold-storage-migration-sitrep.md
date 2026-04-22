# SITREP — Lane C Phase 4 Cold Storage Migration

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase4-cold-storage-migration`
**Phase:** Lane C, Phase 4, Tasks 4.7–4.8 — second of three Phase 4 PRs
**Spec:** `docs/stage1/refounding-ba.md` §Phase 4 Tasks 4.7–4.8
**Archive repo:** https://github.com/mconn0330-svg/hammerfall-v1-archive

## Scope executed

Pre-refounding pipeline work extracted to a separate repository with full git
history preserved, then removed from the main hammerfall-solutions repo. This
finalizes the architectural scope of main as JARVIS-first (Helm + cognitive
subsystems only).

This is **PR 2 of 3** for Phase 4:
1. PR #82 (merged) — heavy-doc currency pass.
2. **This PR** — cold-storage migration (file removals only).
3. Feats framework placeholder (Tasks 4.9–4.10).

A separate follow-up PR (PR 2b) will scrub references to the cold-storaged
paths from surviving living docs and rewrite Routine 5 — see Out of Scope.

## Archive repo created

**URL:** https://github.com/mconn0330-svg/hammerfall-v1-archive
**Visibility:** public (matches the README link inserted in PR #82).
**History:** 100 commits preserved via `git filter-repo --paths-from-file`.
**README:** added per spec; explains the pipeline's status and Stage 4 Feat-restoration plan.

The filtered history was extracted from a fresh clone of hammerfall-solutions at
commit `a711bd7` (PR #82 merge). The filter kept only the paths in the
cold-storage list and dropped everything else from history.

## Files removed from main (51 total)

Top-level paths removed per the spec list:

| Path | Type |
|---|---|
| `bootstrap.sh` | script |
| `staging_area/` | directory (7 files) |
| `project_structure_template/` | directory (32 files) |
| `agents/muse/` | directory (6 files) |
| `agents/scout/` | directory (6 files) |
| `agents/shared/session_protocol.md` | file |
| `scripts/sync_projects.sh` | script |
| `active-projects.md` | file |
| `agents/helm/memory/LongTerm/bootstrap_test_run_Launch.md` | memory snapshot |
| `agents/helm/memory/LongTerm/dummy-app_Launch.md` | memory snapshot |

Total file count: 51 deletions. (Spec estimate was ~45 — the directories
expanded slightly differently in the working tree.)

## Memory preserved in main

Per spec, two `agents/helm/memory/LongTerm/*.md` files **stay** in main:
- `FoundingSession.md`
- `MEMORY_INDEX.md`

These are Helm's own foundational memory, not pipeline project artifacts.

## Verification

**Archive repo populated:**
```
$ git ls-remote https://github.com/mconn0330-svg/hammerfall-v1-archive.git main
f20f681...  refs/heads/main  ← README commit on top of 100 filtered commits
```

**Main repo file removals staged cleanly:**
- `git status` shows 51 file deletions, no other changes.
- All paths in the spec's removal list are gone.
- All paths NOT in the removal list (FoundingSession.md, MEMORY_INDEX.md, etc.) remain intact.

**Filter integrity check:**
- Archive repo top-level: `active-projects.md`, `agents/`, `bootstrap.sh`, `project_structure_template/`, `scripts/`, `staging_area/` — exactly the kept paths.
- `agents/` in archive contains only: `muse/`, `scout/`, `shared/session_protocol.md`, `helm/memory/LongTerm/{bootstrap_test_run,dummy-app}_Launch.md`. No other agents leaked into archive.

## Spec deviations

**None.** PR is exactly the spec's Step 5 (file removals). Reference scrubs
deferred to a follow-up PR by explicit decision (see Out of Scope).

## Out of scope (carry-forward to PR 2b — reference scrub)

Three living docs in the main repo still reference paths that are now removed.
Maxwell decided to ship this PR as file-removals-only and follow up with a
focused reference-scrub PR rather than scope-add. The follow-up PR handles:

1. **`hammerfall-config.md`** — two references to `bootstrap.sh` (lines 3, 29).
   Scrub both.

2. **`services/helm-runtime/supabase_client.py`** — module docstring lists
   `sync_projects.sh` as an example caller of brain.sh. Scrub the example list.

3. **`agents/helm/helm_prompt.md`** —
   - Line 569: link to `agents/shared/session_protocol.md` (cold-storaged).
     Update or remove.
   - Routine 5 (lines 759–770): currently calls `scripts/sync_projects.sh`
     (cold-storaged). **Rewrite as a single-project snapshot trigger** (not
     delete) — the brain-state snapshot pattern still applies; only the
     multi-project sync is gone.

## Pre-flight discoveries

- `git filter-repo` was not installed; required `scoop install git-filter-repo`
  on Maxwell's machine. Python 3.14.4 also installed via scoop alongside
  (broadly useful for tooling, also resolves prior bumps with `python3` in
  parked plans like the Supabase Brain Migration).
- The Phase 4 spec assumed `pip install git-filter-repo`; on this Windows
  environment that path didn't work because there was no Python interpreter on
  PATH. Documenting here so any future cold-storage-style migration knows to
  reach for scoop, not pip.

## STOP gate

Standing by for Maxwell QA. After approval + merge, PR 2b (reference scrub +
Routine 5 rewrite) opens immediately.
