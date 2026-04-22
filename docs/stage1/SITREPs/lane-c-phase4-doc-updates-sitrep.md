# SITREP — Lane C Phase 4 Doc Updates

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase4-readme-rewrite`
**Phase:** Lane C, Phase 4, Tasks 4.1–4.6 — first of three Phase 4 PRs
**Spec:** `docs/stage1/refounding-ba.md` §Phase 4
**Architectural rationale:** `docs/founding_docs/Helm_The_Ambient_Turn.md`

## Scope executed

Heavy-doc currency pass. Brings the README, the global behavior directive, the
global config, the tier protocol, and the three living agent contracts into
alignment with the Ambient Turn end-state (four cognitive subsystems, Thor at T3,
no Quartermaster, no pipeline-era role names).

This is **PR 1 of 3** for Phase 4:
1. **This PR** — doc updates (Tasks 4.1–4.6).
2. Cold-storage migration to `hammerfall-v1-archive` (Tasks 4.7–4.8).
3. Feats framework placeholder (Tasks 4.9–4.10).

## Files changed

| File | Change |
|---|---|
| `README.md` | Full rewrite per spec target structure. AAO/pipeline framing removed. Now positions the project as building Helm (ambient intelligence). Quick start: `docker-compose up` from `services/helm-runtime/` (no real deployment instructions to preserve from the old README). |
| `hammerfall-config.md` | T3 hardware: `DGX Spark` → `Thor (RTX 6000 Ada, 85GB VRAM, MIG partitioning)` hosting all four cognitive subsystems concurrently. Quartermaster productization comment removed. |
| `management/COMPANY_BEHAVIOR.md` | (1) `.docx` directive flipped: formal artifacts (PRDs, UX guides, blueprints, briefs, SITREPs, SWOTs) are now `.docx` AND chat-summarized; routine outputs stay Markdown. (2) Pipeline-era rules removed: PM-assignment rule, Replit/`develop` branch flow in PR-First, FE-Dev-adopts-Replit-components paragraph, 3-Round Debate (Doer/Helm dynamic). (3) New §5 *Disagreement and Honest Feedback* preserves the no-sycophancy/correction-handling principle the spec called out. (4) "Notice to all agents" → "Notice to Helm". |
| `agents/shared/tier_protocol.md` | T3 hardware Thor; Quartermaster productization line removed; Contemplator added to T2 agent list (inner-monologue passes between sessions), T3 agent list, hardware-by-tier table, and Tasker stack composition. |
| `agents/helm/projectionist/projectionist.md` | One-word T3 hardware update: DGX Spark → Thor. |
| `agents/helm/archivist/archivist.md` | Same: DGX Spark → Thor. |
| `agents/shared/session_protocol.md` | Stage 4 daemon reference: DGX Spark → Thor. |
| `services/helm-runtime/model_router.py` | Health-cache comment scrubbed of Quartermaster reference; replaced with neutral "external pollers." |

### Untouched (intentional)

| File | Why |
|---|---|
| `agents/helm/contemplator/contemplator.md` | Pre-flight grep: zero DGX/Speaker/Quartermaster references. Already clean. |
| `docs/founding_docs/Helm_The_Ambient_Turn.md` | Mentions "DGX Spark to Thor" pivot as the *historical reason* Speaker became obsolete. This is canonical narrative and correct in context. |
| `docs/stage0/**`, `docs/stage1/SITREPs/*`, `docs/stage1/ba3-*.md` | Historical, bannered (PR #80) or operating SITREPs. Not touched. |
| `agents/helm/memory/**` | Memory snapshots reflect what was true at the time. Not living contracts. |
| `supabase/migrations/*.sql` | Immutable migration history. |

## Spec deviations

### Deviation #1 — `agents/shared/tier_protocol.md` T2 list adds Contemplator with implied behavior

The T2 AGENTS section originally listed three subsystems with their T2-specific
trigger behavior (Prime initiates on schedule, Projectionist pre-loads frames,
Archivist batches writes). Spec calls for a four-agent roster everywhere.
Adding Contemplator required describing what it does at T2.

Chose: *"Contemplator runs inner-monologue passes between sessions."* Rationale:
this is the agent's defined purpose (`agents/helm/contemplator/contemplator.md`)
and the only T2-relevant behavior (between-session inner life is exactly the kind
of thing a scheduler enables).

Risk if wrong: a one-line behavioral hint in a tier doc; trivially editable when
Contemplator's T2 trigger model is formalized.

### Deviation #2 — Scope-added two living-doc updates not in Task 4.5's three-file list

Task 4.5 enumerated only `archivist.md`, `contemplator.md`, `projectionist.md` for
the light scrub. Repo-wide grep surfaced two additional living references to
DGX Spark / Quartermaster that the spec did not list:

- `agents/shared/session_protocol.md:57` — "Stage 4 (DGX Spark daemon)" → "Stage 4 (Thor daemon)"
- `services/helm-runtime/model_router.py:325` — Quartermaster polling comment → "external pollers"

Both are living code/contract artifacts. Leaving them stale would defeat the
point of the doc-currency pass. Treated as scope-add and flagged here per Lane C
SITREP discipline. Risk if wrong: each is one line; trivial to revert.

### Deviation #3 — `COMPANY_BEHAVIOR.md` removed §5 *3-Round Debate* entirely

The 3-Round Debate section described a Doer-vs-Helm dispute resolution flow.
With pipeline doer agents cold-storaged, the dynamic doesn't exist. Two options:

- (a) Keep the section, reframe Helm-vs-Maxwell — but Helm-vs-Maxwell is just
  "honest feedback + Maxwell decides," not a structured 3-round protocol.
- (b) Remove the section, add a shorter *Disagreement and Honest Feedback*
  section that captures the principle the spec explicitly called out as core
  ("no sycophancy, honest feedback, correction handling").

Chose (b). The new §5 is shorter and more accurate to the post-refounding
operational model. Flagging because this is a structural rewrite, not just a
scrub.

### Deviation #4 — `COMPANY_BEHAVIOR.md` simplified §3 PR-First Rule

Original §3 enumerated the Replit→`develop`→`main` branch model as the canonical
example. With pipeline-era branch flow cold-storaged, the examples no longer
apply. Replaced with a one-paragraph statement of the principle: feature
branches → PR → `main`. Principle preserved; pipeline-specific examples removed.

### Deviation #5 — `COMPANY_BEHAVIOR.md` §4 Technical Baseline kept but trimmed

Removed the Replit `replit/ui-v1` bullet (pipeline-era branch model) and the
"FE Dev adopts Replit components directly. Antigravity wires them to the
backend" sentence (pipeline-era role assignment). Web/Mobile/Backend/Hosting
stack notes retained — those are general Hammerfall stack defaults, not
pipeline-specific.

## Pre-flight discoveries

- `agents/helm/contemplator/contemplator.md` — already clean (pre-flight grep:
  zero DGX/Speaker/Quartermaster matches). No change required.
- `agents/helm/archivist/archivist.md` and `projectionist.md` — each had
  exactly one DGX Spark reference; trivial to update.

## Verification

```
# Living-doc DGX Spark / Quartermaster sweep:
$ grep -r "DGX Spark\|Quartermaster" --include="*.md" --include="*.py" \
    agents/ services/ scripts/ management/ README.md hammerfall-config.md
# (no output)
```

Remaining matches are all expected: stage0 historical docs (bannered), Lane C
SITREPs (operating records), the active spec, memory snapshots, the immutable
migration SQL, and the Ambient Turn rationale doc (where "DGX Spark to Thor"
pivot is canonical narrative).

Speaker references in `agents/`: zero. Phase 3.3 scrub holds.

## Out of scope (covered by Phase 4 PRs 2 and 3)

- Cold-storage migration of `bootstrap.sh`, `staging_area/`, `project_structure_template/`,
  `agents/muse/`, `agents/scout/`, `agents/shared/session_protocol.md`,
  `scripts/sync_projects.sh`, `active-projects.md`, and pipeline-era
  `LongTerm/*Launch.md` snapshots → PR 2.
- `founding_docs/Feats_Framework_Placeholder.md` creation → PR 3.
- The COMPANY_BEHAVIOR.md §7 Memory Protocol references to `brain.sh`,
  `snapshot.sh`, `BEHAVIORAL_PROFILE.md`, etc. — preserved as-is. The brain
  story is unchanged by the refounding; only the per-project agent prompts that
  *call* `brain.sh` are being cold-storaged.

## STOP gate

Standing by for Maxwell QA. After approval + merge, PR 2 (cold storage) opens.
