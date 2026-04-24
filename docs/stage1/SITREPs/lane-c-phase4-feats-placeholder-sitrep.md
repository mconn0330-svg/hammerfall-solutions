# SITREP — Lane C Phase 4 Feats Framework Placeholder

**Date:** 2026-04-23
**Branch:** `feature/lane-c-phase4-feats-placeholder`
**Phase:** Lane C, Phase 4, Tasks 4.9–4.10 — third of three Phase 4 PRs
**Spec:** `docs/stage1/refounding-ba.md` §Phase 4 Tasks 4.9–4.10

## Scope executed

Created the Feats framework placeholder doc that preserves Stage 4 design
thinking ahead of formal Stage 4 architectural work. Content is verbatim from
the spec.

This is **PR 3 of 3** for Phase 4:
1. PR #82 (merged) — heavy-doc currency pass.
2. PR #83 (merged) — cold-storage migration.
3. **This PR** — Feats framework placeholder + scope-add README path fix.

After this PR merges, Phase 4 closes and Phase 5 (close validation + final
SITREP) begins.

## Files added

| Path | Type |
|---|---|
| `docs/founding_docs/Feats_Framework_Placeholder.md` | new doc |

## Files modified (scope-add)

| Path | Change |
|---|---|
| `README.md` | Three `founding_docs/` → `docs/founding_docs/` path fixes (lines 8, 13, 18) |

## Spec deviations

### Deviation #1 — Path: spec says `founding_docs/`, actual location is `docs/founding_docs/`

The spec instructs creating `founding_docs/Feats_Framework_Placeholder.md` (bare
root path). The repo's actual canonical-docs location is `docs/founding_docs/`,
which already contains `Helm_The_Ambient_Turn.md`, `Helm_Roadmap.md`, and
`README.md`. I created the file at `docs/founding_docs/Feats_Framework_Placeholder.md`
to match the existing structure.

The spec's bare-`founding_docs/` references appear to be a longstanding template
typo — the Lane C Phase 2 prompt rewrite SITREP (PR #76) already noted the same
mismatch and used the actual path. No restructure needed; the placeholder
belongs alongside its sibling founding docs.

I also corrected the placeholder's own internal canonical-reference link
(spec line 1054 says `founding_docs/Helm_Roadmap.md`; I wrote
`docs/founding_docs/Helm_Roadmap.md`) so the link actually resolves.

### Deviation #2 — Scope-add: README.md broken founding_docs links

PR #82 (the heavy-doc currency PR) shipped `README.md` from the spec verbatim,
which carried the same bare-`founding_docs/` paths. As a result, three live
references in the README do not resolve today:

- Line 8: `[founding_docs/Helm_The_Ambient_Turn.md](founding_docs/Helm_The_Ambient_Turn.md)` — broken
- Line 13: `See [founding_docs/Helm_Roadmap.md](founding_docs/Helm_Roadmap.md)` — broken
- Line 18: `` `founding_docs/` — canonical reference documents `` — wrong directory listed

These three lines were updated in this PR to use `docs/founding_docs/`. The
fixes are mechanical, in the same bug class as the placeholder path question,
and shipping the placeholder while leaving the README's links broken would be
churn. Bundled into this PR rather than a separate one-line PR.

Verified via grep: no other live (non-spec, non-historical) doc references
bare `founding_docs/`. All other repo references (helm_prompt.md, prior
SITREPs, archive READMEs, frozen historical docs) already use the correct
`docs/founding_docs/` path.

## Verification

**Placeholder file exists:**
```
$ ls docs/founding_docs/
Feats_Framework_Placeholder.md
Helm_Roadmap.md
Helm_The_Ambient_Turn.md
README.md
```

**README links resolve:**
- `docs/founding_docs/Helm_The_Ambient_Turn.md` — exists
- `docs/founding_docs/Helm_Roadmap.md` — exists

**Placeholder content matches spec:** verbatim copy of `refounding-ba.md` lines
991–1055, with the single canonical-reference path fix noted above.

## Out of scope (carry-forward to Phase 5)

Phase 5 close validation (per spec lines 1066–1071):
- All doc updates merged ✓ (after this PR)
- Archive repo exists, has history, has README ✓
- Main repo no longer contains cold-storage files ✓
- README.md, hammerfall-config.md, COMPANY_BEHAVIOR.md, tier_protocol.md all
  reflect refounding ✓
- Feats placeholder exists in `docs/founding_docs/` ✓ (after this PR)

Plus: runtime boot smoke test (/health, /config/agents shows 4 agents, no
Speaker residue).

## STOP gate

Standing by for Maxwell QA. After approval + merge, Phase 5 close validation
runs and the Lane C refounding closes.
