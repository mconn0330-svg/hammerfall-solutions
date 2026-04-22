# SITREP — Lane C Phase 3.2: Speaker Contract Archival

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase3-speaker-contract-archival`
**Phase:** Lane C, Phase 3, Tasks 3.6–3.7
**Spec:** `docs/stage1/refounding-ba.md`
**Architectural rationale:** `docs/founding_docs/Helm_The_Ambient_Turn.md` §4

## Scope executed

Archived the Speaker contract from its live agent location to a deprecated archive directory, with a README explaining what Speaker was, why it was deprecated, why we kept the contract instead of deleting it, and how to read it as a historical document.

This is **sub-PR 2 of 3** for Phase 3:
1. PR #78 (merged) — code deletion (runtime, config, model pulls, stress tests).
2. **This PR** — contract archival.
3. Sub-PR 3 (planned) — reference scrub from living documents + historical-doc banners.

## Files changed

| File | Change |
|---|---|
| `agents/helm/speaker/speaker.md` → `docs/archive/speaker-deprecated/speaker.md` | `git mv`. Contract preserved verbatim. |
| `agents/helm/speaker/` (directory) | Removed (empty after the move). |
| `docs/archive/speaker-deprecated/README.md` | New. Deprecation rationale, what to read the contract for, what is obsolete vs. what is design heritage worth preserving. |
| `docs/archive/` (directory) | New. First archive entry; will likely host other deprecated artifacts as Lane C close-out continues. |

## Why a README accompanies the archive

The spec says "archive the Speaker contract." A bare `git mv` would technically satisfy that — but a future reader hitting `docs/archive/speaker-deprecated/speaker.md` cold has no way to know:

- whether the contract is *current* (just at a new path) or *deprecated* (kept for history)
- which sections are obsolete vs. which still carry design value
- what replaced it and where the rationale lives
- when it was archived and which PR removed the code

The README answers all four questions in one place. Roughly half a page of text against a 94-line contract — proportional, not over-documented.

## Spec deviations

### Deviation #1 — Removed the now-empty `agents/helm/speaker/` directory

The spec says `git mv agents/helm/speaker/speaker.md docs/archive/speaker-deprecated/speaker.md`. After the move, `agents/helm/speaker/` is empty. Git doesn't track empty directories, so the move alone leaves a phantom empty directory on disk that doesn't appear in `git status`. I removed it (`rmdir agents/helm/speaker`) so the working tree matches what other contributors will see after `git pull`.

Risk if wrong: an empty directory reappears for any contributor who created it locally before this change. Trivial.

### Deviation #2 — Created `docs/archive/` as a new top-level archive root

The spec doesn't specify where the archive directory should live. Options considered:

- `docs/archive/speaker-deprecated/` — chosen. Reads naturally; `docs/` is already where reference material lives; future deprecations slot in as siblings.
- `docs/stage1/archive/` — rejected. Stage 1 is the *current* phase; archives outlive phases.
- `archive/` (top-level) — rejected. New top-level dir is heavier; `docs/` is fine.

Flagging because this is a structural decision that future archive work will inherit.

## Verification

- `git status` shows the rename cleanly: `renamed: agents/helm/speaker/speaker.md -> docs/archive/speaker-deprecated/speaker.md`
- `git log --follow docs/archive/speaker-deprecated/speaker.md` (post-merge) will trace the file's full history through the move.
- `agents/helm/` now contains only live cognitive subsystems: `archivist/`, `contemplator/`, `projectionist/`, `helm_prompt.md`, `memory/`. Speaker dir is gone.
- No code references `agents/helm/speaker/speaker.md` (PR #78 removed all imports). A grep against the post-archival tree returns zero hits in `services/helm-runtime/`.

## Out of scope

- **Reference scrub** — deferred to sub-PR 3 (`feature/lane-c-phase3-speaker-ref-scrub`). Files still referencing Speaker by name in a present-tense sense include `hammerfall-config.md`, `agents/shared/tier_protocol.md`, the other live agent contracts (archivist/contemplator/projectionist), and `COMPANY_BEHAVIOR.md`. Historical documents in `docs/ba1-5/`, `docs/ba6-9/`, `docs/stage0/`, and `docs/stage1/` will get historical-document banners rather than scrubs.
- **Speaker-related env vars and helper scripts outside `services/helm-runtime/`** — none identified yet, but sub-PR 3 will sweep for any.

## STOP gate

Standing by for Maxwell QA before opening sub-PR 3 (reference scrub).
