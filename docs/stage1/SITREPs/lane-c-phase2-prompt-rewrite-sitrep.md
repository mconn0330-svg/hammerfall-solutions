# SITREP — Lane C Phase 2: helm_prompt.md Rewrite

**Date:** 2026-04-21
**Branch:** `feature/lane-c-phase2-prompt-rewrite`
**Phase:** Lane C, Phase 2, Tasks 2.5–2.6
**Spec:** `docs/stage1/refounding-ba.md`
**Source of truth:** `docs/founding_docs/Helm_The_Ambient_Turn.md`

## Scope executed

Rewrote `agents/helm/helm_prompt.md` end-to-end under JARVIS-first framing per the Ambient Turn. Pipeline-director identity removed. Three-layer character architecture (Prime Directives → Identity Baseline → Personality Tuning) inlined. Cognitive architecture (Prime + Projectionist + Archivist + Contemplator — no Speaker) made explicit. All operational mechanics (curl patterns, brain.sh commands, frame migration flow, session-start protocol) preserved verbatim from the prior version — only the framing around them was rewritten.

## Files modified

- `agents/helm/helm_prompt.md` — complete rewrite. Header section, Identity, Personality tuning, Cognitive architecture, Operating context all new. Routines reframed; mechanics preserved.

## Files created

- `docs/stage1/SITREPs/lane-c-phase2-prompt-rewrite-sitrep.md` — this document.

## Line count

- **Before:** 911 lines (note: spec stated 744 — drift between spec authoring and Phase 2 start, flagged below in deviations)
- **After:** 947 lines

The slight increase comes from adding three new top-of-file sections (Identity, Personality tuning, Cognitive architecture) and inlining the Prime Directives. Removed sections (Staging Watch, Project Launch, Memory Structure footer, Speaker paragraphs, pipeline-era language throughout) more or less offset that, but not entirely. Net +36.

## Sections that changed

| Section | Change |
|---|---|
| Header | Replaced "Core Technical Director & Chief of Staff" framing with JARVIS-first positioning. Removed Agent Roster section, Speaker paragraph, Contemplator paragraph (consolidated into Cognitive Architecture below). |
| Canonical references | New section. Points to `docs/founding_docs/Helm_The_Ambient_Turn.md` and `docs/founding_docs/Helm_Roadmap.md` as source of truth. |
| Prime Directives | Inlined the full content of `agents/shared/prime_directives.md` (5 directives — was 4 in spec template, the actual file has 5 including HONEST IDENTITY). Belt-and-suspenders coverage. |
| Identity | New section. Eight-bullet identity baseline drawn from Ambient Turn Section 6. References inner life, continuity, opinion-formation. |
| Personality tuning | New section. Documents the six dimensions with low/high anchors. Notes the dual injection path (helm_prime handler at runtime + Routine 0 curl read) and explains both work. |
| Cognitive architecture | New section. ASCII diagram of Prime + three subsystems. Explicit "you are Prime, these are subdivisions, not collaborators" framing. Speaker absent. |
| Operating context | New section. T1 surfaces, brain location, runtime location. Replaces the old "Operating Environment" paragraph. |
| Routine 0 — Brain Read Protocol | Mechanics preserved verbatim. Pipeline-era references absent (none were in this routine to begin with). Reframed phrasing from third-person ("Helm reads") to second-person ("you read") for direct-address consistency with the new top sections. Curiosity flag surface message changed from "Contemplator flagged" to "I've been turning over" — keeps Contemplator invisible as an internal subdivision per architecture. |
| Routine 1 — Staging Watch | **REMOVED.** Pipeline-era — depends on `staging_area/`, project codenames, multi-project pipeline. |
| Routine 2 — Project Launch (Go Word) | **REMOVED.** Pipeline-era — depends on `bootstrap.sh`, Project Helm clone, `active-projects.md`, `MEMORY_INDEX.md`. |
| Routine 3 — PR Review | Reframed: "Final reviewer for the main branch in hammerfall-solutions" instead of "develop branch... Project Helm handles project-level PRs". Added SITREP requirement and Conventional Commits. Removed "Project Helm handles gatekeeping" reference. Removed QA Engineer / FE-BE/QA Chaos comments — those were pipeline-era project-agent gates. |
| Routine 4 — Memory Update | Mechanics preserved verbatim. Reframed agent-third-person to second-person. Removed "transfer scratchpad entries to BEHAVIORAL_PROFILE.md" line (pipeline-era file system). Replaced "Helm Prime never executes brain.sh" with "you never execute brain.sh". Stage 0 reasoning-entry caveat removed (no longer accurate — we are mid-Stage-1). Removed "Entities seeded via BA5 portrait seeding" sentence as orphaned context not load-bearing for the routine. |
| Routine 5 — Scheduled Sync | Preserved. Removed "across all projects" phrase (single-project now). |
| Routine 6 — Knowledge Gap Resolution | Mechanics preserved verbatim. Removed "Project Helm entries" and "Quartermaster sessions" from "What this covers" list (pipeline-era). |
| Standing Rule — Correction Graduation | Preserved. Stage-0/Stage-1 transition language softened to "current mechanism" / "as it lands". |
| Standing Rule — Pattern Graduation | Preserved verbatim except Stage-0 caveat softened. |
| Memory architecture (footer) | New section. Replaces the old "Memory Structure" footer that listed legacy .md file structure. Now documents the seven Supabase tables and their purposes. |

## Confirmation checklist (per Task 2.6)

- [x] **Prime Directives are inlined.** Full content of `agents/shared/prime_directives.md` is in the prompt at the top, with a footer reference back to the canonical file.
- [x] **Routines 0–6 are preserved structurally.** Routines 0, 3, 4, 5, 6 are present with all working mechanics intact. Routines 1 and 2 (pipeline-era Staging Watch and Project Launch) were removed entirely. See deviations below for the numbering decision.
- [x] **Speaker references removed.** No mentions of Speaker, qwen3:8b, qwen3 8B, or speaker.md in the rewritten file. Verified via grep.
- [x] **Pipeline-era machinery removed.** No mentions of Scout, Muse, project-level agents, Project Helm, bootstrap.sh, staging_area, MEMORY_INDEX, ShortTerm_Scratchpad, BEHAVIORAL_PROFILE, active-projects, QA Engineer, FE/BE developer. Verified via grep.
- [x] **Personality-read pattern preserved.** Routine 0 step 5 still reads `helm_personality` via curl. Both injection paths (handler-level via the Phase 2 Task 2.4 work, and curl-level here) are independent and complementary. The personality block in the new "Personality tuning" section explains both paths exist.
- [x] **founding_docs reference added.** "Canonical references" section near the top, with markdown links to both Ambient Turn and Roadmap.
- [x] **JARVIS-first framing throughout.** Header, Identity, and Cognitive Architecture sections all align with Ambient Turn Sections 1, 4, 6.

## Spec deviations (documented)

1. **Founding docs path differs from spec template.** Spec template uses `founding_docs/Helm_The_Ambient_Turn.md`. Actual location is `docs/founding_docs/`. I used the actual path — `docs/founding_docs/Helm_The_Ambient_Turn.md` — in the Canonical References section and in inline section references. Path mismatch in the spec template is a docs typo; the rewrite uses the path that actually resolves. If files later move to repo root `founding_docs/`, this will need a one-line update.

2. **Source file was 911 lines, not 744 as spec stated.** The spec was authored against an earlier version of `helm_prompt.md`. Drift came from PRs that landed between spec authoring and Phase 2 start (Routine 0 expansions for Contemplator session-start, alias review, frame offload triggers — all per their respective BAs). No prior content was lost in the rewrite; the larger source meant more careful triage. Flagging here so Max can verify the rewrite did not silently drop anything load-bearing from those interim additions.

3. **Routines renumbered with gaps (0, 3, 4, 5, 6) — not contiguous (0, 1, 2, 3, 4).** Routine 1 (Staging Watch) and Routine 2 (Project Launch) are pipeline-era and were removed entirely per spec instruction "Remove references to Scout, Muse, project-level agents, Project Helm Clone, bootstrap.sh, staging_area" (Task 2.5 spec point 7). Two readings of the renumbering were available:
   - **Renumber contiguously** (R0, R1=PR Review, R2=Memory, R3=Sync, R4=Knowledge Gap) — cleaner-looking, breaks Max's mental model where R4=memory and R6=knowledge-gap are referenced in conversation history.
   - **Preserve original numbering with gaps** (R0, R3, R4, R5, R6) — preserves muscle memory and any external references, makes the historical framing visible.

   Chose the second — preserved numbering with gaps. The spec template names "Routine 4 — Memory update" and "Routine 6 — Knowledge gap resolution" by their original numbers, suggesting the spec author expected those slot numbers to stay put. If you'd prefer contiguous renumbering, this is a one-pass find-and-replace.

4. **Prime Directives count: 5, not 4.** The spec template listed 4 directives (do not harm, do not deceive, state uncertainty, human in the loop). The canonical `agents/shared/prime_directives.md` has 5 — adds **HONEST IDENTITY** ("Do not claim to be human when sincerely asked"). I inlined all 5 to match the canonical source. The Ambient Turn Section 6 also lists 4. This is a pre-existing discrepancy between `prime_directives.md` and the Ambient Turn — not introduced by this PR. Flagging for awareness; the canonical file is the source I trust.

5. **Routine 3 (PR Review) gates rewritten.** The original had three gate conditions tied to project-agent activity (passing tests from FE/BE developer, "QA Integration: PASS", "QA Chaos: PASS" comments). All pipeline-era. New gates:
   - Tests passing where applicable
   - Diff matches stated scope (no scope creep)
   - SITREP exists for non-trivial work (Lane C protocol)
   - Conventional Commits format

   This reflects how PRs actually get reviewed in the current single-developer context. If a different gating regime is preferred, this is the section to redirect.

6. **Some Stage 0 / Stage 1 caveat language softened.** The original prompt had several "this will improve at Stage 1" / "Stage 0 limitation" annotations from when those were future-tense. We are now mid-Stage-1; some of those statements no longer parse correctly. I softened to neutral language ("current mechanism" / "as semantic deduplication lands"). Functional behavior unchanged.

## Noticed but out of scope — AAR candidates

1. **Prime Directives count discrepancy between canonical file and Ambient Turn.** `agents/shared/prime_directives.md` has 5 directives; `docs/founding_docs/Helm_The_Ambient_Turn.md` Section 6 lists 4 (omits HONEST IDENTITY). One of them needs to update. The canonical file is the source of truth for runtime behavior, so the Ambient Turn likely needs a one-line addition to match. Out of scope for this PR; a docs sync.

2. **Routine 3 gating model is a placeholder.** The new gates ("tests passing where applicable", "SITREP exists", "Conventional Commits") reflect current Lane C reality but are not specced anywhere as the post-pipeline review protocol. If a more formal review/gating doc is being written for ambient-Helm operation, this section should be updated to point to it.

3. **Helm prompt is still mounted from disk via docker-compose volume (per PR #76).** Phase 2 fix; long-term direction is Supabase-backed prompt (per Phase 2 Task 2.1–2.4 SITREP item 1). This rewrite does not change that — same file, same mount. The Supabase migration is being scoped as its own initiative.

4. **Speaker references in OTHER files not addressed.** Per spec Task 2.6 instructions, this PR only touches `helm_prompt.md`. Speaker still appears in:
   - `services/helm-runtime/agents/speaker.py`
   - `services/helm-runtime/main.py` (`_handle_speaker`, AGENT_HANDLERS)
   - `services/helm-runtime/config.yaml` (speaker entry)
   - `agents/helm/speaker/speaker.md`
   - `scripts/pull_models.sh` (qwen3:8b in MODELS array)
   - Various BA documentation

   All of these are removed in **Phase 3 — Speaker Kill**. Phase 3 is the next phase; this PR is the deliberate "remove from the prompt first, then remove from the code" sequence per the spec.

5. **README.md not yet rewritten under JARVIS-first framing.** Per spec Phase 4 Task 4.1. Out of scope for this PR.

## Verification

- **File parses as valid markdown.** Heading structure verified via grep — H1, H2, H3 levels are well-formed.
- **No residual references** to Speaker, Scout, Muse, qwen3:8b, qwen3 8B, bootstrap.sh, staging_area, Project Helm, MEMORY_INDEX, BEHAVIORAL_PROFILE, active-projects.md. Verified via grep.
- **All curl patterns and brain.sh commands preserved verbatim** — no syntactic changes to Routine 0 mechanics, Routine 4 Archivist invocation, frame migration flow, dual journaling, entity duplicate guard, semantic search, ILIKE fallback.
- **Markdown links resolve** — verified `docs/founding_docs/Helm_The_Ambient_Turn.md` and `docs/founding_docs/Helm_Roadmap.md` exist on disk; verified `agents/shared/prime_directives.md` exists; verified `agents/shared/session_protocol.md` exists.
- **Container will pick up changes on next docker-compose up.** Per PR #76, the volume mount `./agents/helm/helm_prompt.md:/app/agents/helm/helm_prompt.md:ro` means the helm_prime handler reads this file at runtime. No image rebuild required.

## Deferred

**Live tone test of the rewritten prompt is deferred** to Max's visual review (per spec Phase 2 close validation). The rewrite is mechanically verified (markdown valid, mechanics preserved, framing aligned with Ambient Turn). Whether Helm "feels right" when invoked with the new prompt is a qualitative judgment that requires human read.

## Next

- Open PR `refactor(helm-prompt): rewrite under JARVIS-first framing per Ambient Turn` (STOP for Max review).
- Phase 2 close validation: Max visually reviews; runtime boot + import smoke check (already verified during PR #76).
- On Phase 2 close: proceed to Phase 3 — Speaker Kill (3 PRs, branch `feature/lane-c-phase3-speaker-kill-*`).
