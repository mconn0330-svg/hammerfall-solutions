# SITREP — Lane C Phase 3.3: Speaker Reference Scrub

**Date:** 2026-04-22
**Branch:** `feature/lane-c-phase3-speaker-ref-scrub`
**Phase:** Lane C, Phase 3, Tasks 3.8–3.9 — closes Phase 3
**Spec:** `docs/stage1/refounding-ba.md`
**Architectural rationale:** `docs/founding_docs/Helm_The_Ambient_Turn.md` §4

## Scope executed

Final Phase 3 sub-PR. Scrubs Speaker from living documents and adds historical-document banners to docs that predate the Ambient Turn. After this merges, the post-Ambient Turn architecture (Helm Prime + Projectionist + Archivist + Contemplator, no Speaker) reads cleanly to anyone walking in cold.

This is **sub-PR 3 of 3** for Phase 3:
1. PR #78 (merged) — runtime code deletion.
2. PR #79 (merged) — contract archival.
3. **This PR** — reference scrub + historical banners.

## Files changed

### Surgical scrub (3 files)

| File | Change |
|---|---|
| `hammerfall-config.md` | T3 hardware comment: removed `+ RTX 4090 (Speaker)`. Added Contemplator to the DGX Spark agent list (it had been omitted entirely — flagged below). |
| `agents/shared/tier_protocol.md` | Removed Speaker from: opening "all five agents" framing, T1 AGENTS line, T2 AGENTS bullet list, T3 AGENTS bullet list, T3 hardware section (now single-node, not two-node), Agent Hardware Assignment by Tier table, Taskers section. |
| `docs/founding_docs/Helm_Roadmap.md` | Line 495: rewrote "Personality injection (via Speaker today; moves to direct injection via Prime handler in Lane C)" as past-tense reflecting that PR #76 already landed the direct injection. |

### Historical-document banners (9 files)

Standardized one-line banner inserted between the H1/H2 title block and the metadata block in each historical doc:

> **Historical document — frozen at the date below.** References to "Speaker" reflect the pre-Ambient Turn architecture. Speaker was deprecated in Lane C Phase 3 (PRs #78 code deletion, #79 contract archival, #80 reference scrub). Current architecture: `docs/founding_docs/Helm_The_Ambient_Turn.md`. Deprecation rationale: `docs/archive/speaker-deprecated/`.

- `docs/stage0/helm-stage0-summary.md`
- `docs/stage0/ba1-5/helm-system-design-ba1-5.md`
- `docs/stage0/ba6/helm-system-design-ba6.md`
- `docs/stage0/ba7/helm-system-design-ba7.md`
- `docs/stage0/ba7/ba7-spec.md`
- `docs/stage0/ba8/helm-system-design-ba8.md`
- `docs/stage0/ba9/helm-system-design-ba9.md`
- `docs/stage1/ba3-close.md`
- `docs/stage1/ba3-agent-model-selection.md`

Active SITREPs in `docs/stage1/SITREPs/` and the spec `docs/stage1/refounding-ba.md` were intentionally **not** bannered — those are operating documents, not historical state.

### Untouched (Speaker references intentional)

| File | Why untouched |
|---|---|
| `services/helm-runtime/middleware.py:286` | "post-Speaker architecture" — historical context phrase, intentional. |
| `docs/founding_docs/Helm_The_Ambient_Turn.md` | Names Speaker as the deprecated layer; this IS the canonical deprecation rationale. |
| `docs/archive/speaker-deprecated/speaker.md` | Archived contract, preserved verbatim by design (PR #79). |
| `docs/archive/speaker-deprecated/README.md` | Deprecation README authored in PR #79 — already correct. |
| `docs/stage1/SITREPs/lane-c-phase2-*` and `lane-c-phase3-*` | Active SITREPs document the Speaker kill; references to Speaker are necessary. |
| `docs/stage1/refounding-ba.md` | The spec we are executing — describes Speaker removal as an in-progress task. |
| `helm-ui/src/data/mockData.js` | Different developer's UI work, untracked in this branch, out of scope. |

## Pre-flight scope check (memory-vs-reality)

The Phase 3 resume memory note expected scrubs in `archivist.md`, `contemplator.md`, `projectionist.md`, and `COMPANY_BEHAVIOR.md`. Pre-flight grep on each: **zero Speaker references**. Those were already clean — likely scrubbed organically during BA3 work or never had Speaker mentions to begin with. The scrub scope on living docs is therefore much smaller than the memory note implied.

`docs/founding_docs/Helm_Roadmap.md` was **not** in the memory note's scrub list, but a grep surfaced one stale "via Speaker today" line. Treated as scope-add rather than skip — the Roadmap is a living doc and that line is now factually wrong. Flagged below as Deviation #1.

## Spec deviations

### Deviation #1 — Scope-added `docs/founding_docs/Helm_Roadmap.md`

The Phase 3 resume memory note did not list `Helm_Roadmap.md` for scrubbing. The original Phase 3 spec (Tasks 3.8–3.9) called out a more prescribed list. I scope-added one line in the Roadmap because:

- The Roadmap is a living document (it tracks current state of the project, not historical state).
- The line ("Personality injection (via Speaker today; moves to direct injection via Prime handler in Lane C)") is now factually wrong — PR #76 landed the direct injection, Speaker is gone.
- A SITREP entry referencing the Roadmap as "almost-correct except this line" is worse than just fixing the line.

Risk if wrong: a one-line factual correction in a roadmap document. Trivial to revert.

### Deviation #2 — Added Contemplator to `hammerfall-config.md` T3 hardware list

The original line read:
```
# T3 — DGX Spark (Helm Prime, Projectionist, Archivist) + RTX 4090 (Speaker)
```

After removing `+ RTX 4090 (Speaker)` the surviving list still omits Contemplator entirely. Two options:
- Strict scope: leave `(Helm Prime, Projectionist, Archivist)` — known-incomplete.
- Scope-add: append Contemplator → `(Helm Prime, Projectionist, Archivist, Contemplator)` — reflects current architecture.

Chose scope-add. Leaving a known-incomplete list because "Contemplator currency is a separate doc cleanup" puts a misleading config comment in front of every reader, and the fix is one word.

Flagging because future doc-currency work may want to re-audit this line against final T3 model assignments (e.g., whether Contemplator stays on the Spark or moves to a different partition).

### Deviation #3 — Did NOT add Contemplator to `tier_protocol.md` while scrubbing Speaker

Tier protocol's "all five agents" claim originally meant Helm Prime + Projectionist + Archivist + Speaker + (one more, never specified) — Contemplator was never added when BA3 introduced it. Three options when scrubbing Speaker:

- (a) Leave the count alone, just remove Speaker → "all five" becomes "all four" implicitly with three named, off by one.
- (b) Add Contemplator everywhere Speaker was, get the count right → significant scope-add, restructures the doc.
- (c) Make the framing count-agnostic ("all cognitive subsystems") and remove Speaker — chosen.

Option (c) is the minimal correct scrub. Adding Contemplator to T2 bullets, T3 bullets, the hardware table, and the Taskers section is a separate concern (BA3 doc currency, not Speaker scrub). That work belongs in Phase 4 doc updates.

The doc now reads as Speaker-free and count-agnostic but still under-represents Contemplator. Flagging clearly so Phase 4 picks it up.

### Deviation #4 — `tier_protocol.md` T3 hardware now claims "single-node" instead of "two-node"

Removing `Speaker → RTX 4090` from the T3 architecture meant the surviving hardware text "DGX Spark + RTX 4090. Two-node architecture" was no longer accurate. Updated to `DGX Spark. Single-node architecture.` This reflects the current Ambient Turn end-state, but should be re-verified against any Phase 5 / Stage 4 hardware planning. A different decision (e.g., Holoscan returning on a separate node) would change this.

### Deviation #5 — `Taskers` section in `tier_protocol.md` rewrote stack composition

Original: "Each Tasker is a full Helm stack (Speaker + Projectionist + Archivist) operating within a bounded project or task context."

Rewrote to: "Each Tasker is a full Helm stack (Helm Prime + Projectionist + Archivist) operating within a bounded project or task context."

Substituted Helm Prime in Speaker's structural slot rather than just deleting Speaker, because a Tasker without a voice-generating component is not a full stack. Helm Prime is the voice-generating component in the post-Ambient Turn architecture. This is a structural rewrite, not a pure scrub — flagging.

Contemplator gap also exists here (a "full Helm stack" should include Contemplator) — same Phase 4 concern as Deviation #3.

## Verification

Repo-wide grep for `[Ss]peaker` against the post-scrub tree:

| Match location | Status |
|---|---|
| `docs/archive/speaker-deprecated/*` | Expected — archived contract + README. |
| `docs/founding_docs/Helm_The_Ambient_Turn.md` | Expected — canonical deprecation rationale. |
| `docs/stage1/SITREPs/*` | Expected — active SITREPs document the kill. |
| `docs/stage1/refounding-ba.md` | Expected — spec describes the Speaker removal task. |
| `docs/stage0/**` (9 docs) | Expected — bannered, contents preserved. |
| `docs/stage1/ba3-*.md` | Expected — bannered, contents preserved. |
| `services/helm-runtime/middleware.py:286` | Expected — "post-Speaker architecture" historical phrase. |
| `helm-ui/src/data/mockData.js` | Out of scope — untracked, different developer's branch. |
| **anywhere else** | None. |

`hammerfall-config.md` and `agents/shared/tier_protocol.md`: zero Speaker matches confirmed by grep.

## Phase 3 close

After this PR merges, **Phase 3 closes**. End-state:

- No Speaker code in the runtime (`services/helm-runtime/`).
- No Speaker entry in `config.yaml` or in `/health` / `/config/agents` responses.
- No Speaker in model pulls (`pull_models.sh`) or stress-test scripts.
- Speaker contract preserved verbatim at `docs/archive/speaker-deprecated/speaker.md` with deprecation rationale README.
- Living docs read as Speaker-free.
- Historical docs carry banners pointing readers to the Ambient Turn rationale.

## Out of scope (deferred to Phase 4 doc updates)

- Adding Contemplator to `agents/shared/tier_protocol.md` agent lists, hardware table, and Taskers stack composition (Deviations #3 and #5).
- Re-verifying T3 hardware framing in `tier_protocol.md` against any Phase 5 / Stage 4 hardware planning (Deviation #4).
- Re-auditing `hammerfall-config.md` T3 hardware comment if Contemplator's MIG partition assignment changes (Deviation #2).
- Any other BA3-era doc-currency drift unrelated to Speaker.

## STOP gate

Standing by for Maxwell QA. After approval + merge, Phase 3 closes and Phase 4 (doc updates reflecting Ambient Turn end-state) opens.
