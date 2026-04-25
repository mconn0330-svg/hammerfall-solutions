# Post-T1 Findings — Queue

|               |                                                                                                                                                                                    |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Status**    | 🟢 Living document                                                                                                                                                                 |
| **Created**   | 2026-04-24                                                                                                                                                                         |
| **Purpose**   | Capture findings, deferrals, and "we noticed this during T1 and chose not to do it now" items so they are not lost between T1 close and Stage 2 planning.                          |
| **Lifecycle** | Append during T1 PRs. Re-sort at T4.5 (T1 close SITREP). First batch is addressed immediately after T1 close — _before_ Stage 2 planning kicks off.                                |
| **Related**   | `docs/founding_docs/Helm_Brain_Object_Types.md` (architectural reference for brain-type findings), `docs/stage1/Helm_T1_Launch_Spec_V2.md` (the spec these findings sit alongside) |

---

## How this document works

Findings are surfaced during V2 execution PRs. Each PR's SITREP can flag items
to add here under one of three sections:

- **First batch — addressed immediately after T1 close:** committed work for the
  first post-T1 cycle. Equivalent to "we know we want this; we just couldn't
  fit it into T1 without scope creep."
- **Open findings — surfaced during T1, deferred:** captured during T1 work
  with a deliberate "not now" call. Re-evaluated at T4.5.
- **Resolved:** moved here after a finding has been addressed (kept for
  institutional memory).

Each finding gets:

- An ID (Finding #NNN, sequential)
- A short title
- The PR / context where it surfaced
- The proposal
- The "why now (or not)" reasoning

This document is the operational queue. Architectural reference for
brain-type findings lives in `docs/founding_docs/Helm_Brain_Object_Types.md`.
Findings that are pure architecture (not specific to T1 deferrals) get
documented there with a pointer here.

---

## First batch — addressed immediately after T1 close

These items form the **post-T1 / pre-T2 cycle** — the bridge between T1
close (runtime + UI + Tier 1/2 brain) and T2 ambient infrastructure. The
common thread: things V2 deliberately scoped out of T1 to keep the runtime
foundational, but that the ambient intelligence vision needs before T2's
scheduled passes will feel meaningful.

T1 PRs may append new findings here. At T4.5 the SITREP confirms which roll
into this cycle vs. which sit in §Open for later Stage 2 planning.

### Finding #002 — Post-T1 / Pre-T2 ambient bridge cycle

**Surfaced:** 2026-04-24, during V2 spec gap review.
**Owner:** TBD post-T1 (sequenced after T4.5 SITREP).
**Reference:** This finding is a _batch_ of related deferrals that cluster
around brain expansion + ambient surfacing — work that belongs together,
not splayed across separate cycles.

**Scope (six items, ordered roughly cheapest-to-most-ambitious):**

1. **Tier 3 brain types from the roadmap.** `helm_goals`, `helm_hypotheses`,
   `helm_anticipations`, `helm_surprises`, `helm_tensions`, `helm_watchlist`,
   `helm_affinities`, `helm_routines`. Reference:
   `docs/founding_docs/Helm_Brain_Object_Types.md` §Tier 3. Each follows
   the T0.B7 sub-PR template (~50 lines in the module proper). Some of
   these only become _meaningful_ once T2 scheduled passes exist — landing
   the tables ahead of T2 lets T2 work focus on cognition, not schema.

2. **Local memory cache for Supabase outage.** Outbox protects writes; reads
   have no fallback. A last-N-entries SQLite cache (refreshed on every
   successful read) would let Helm degrade gracefully from "ambient mind"
   to "knows the recent past" instead of "knows nothing." Probably ~1 PR
   in the memory module.

3. **Claude Code ↔ Helm brain bridge.** Maxwell's daily coding happens in
   Claude Code (a different tool, different brain). Right now Helm has no
   awareness of what Maxwell is building. For "ambient intelligence" to be
   real and not just "another chat app," Claude Code sessions need to
   write into Helm's brain — at minimum: project summaries, key decisions,
   significant file changes. Real ambient gap. Likely needs its own ADR
   and may pull in AGENTS.md scope from T0.A1.

4. **PWA / mobile-native UI shell.** T4.11 ships a Vercel UI that works in
   mobile browsers, but a PWA install adds: home-screen icon, offline
   shell, push-notification permission (sets up #5). Probably ~2 PRs in
   helm-ui. Defer-able if mobile-browser hello-world is enough.

5. **Push notification path.** "Ambient" eventually means Helm initiates —
   surfaces a curiosity, follows up on a promise, flags a watchlist
   change. T1 = Maxwell-initiates. This adds the mechanical path for
   Helm-initiates. Depends on PWA (#4) for the user-facing channel; depends
   on T2 scheduled passes for the trigger source. Lands once both are in.

6. **Voice / multimodal exploration spike.** Not full voice — a _spike_ to
   determine what voice-Helm would require (ASR + TTS choices, latency
   envelope, prompt adaptations for spoken output). Probably ~3 days of
   spike → ADR documenting the path before any commitment to build.
   Honestly closer to Stage 3 than this cycle, but worth a spike here so
   T2 work can be informed.

**Why batched as one finding (not six):** they share a coherent narrative
(ambient bridge), share a stakeholder review point (does T1 hello-world
prove the runtime well enough that we expand cognition vs. fix the
foundation?), and roughly share a sequencing window (after T1 hello-world
proves the runtime, before T2 scheduled-pass infrastructure starts). One
re-sort decision at T4.5 is cleaner than six.

**Why now (this cycle, not in T1):** each individual item is real ambient
work, not foundational. Pulling any single one into T1 would push T1 close
out without changing the runtime's correctness. T0.B7 was the exception
because the memory module was _literally_ hot in everyone's hands during
T0.B1–T0.B6. These items don't have that proximity advantage.

**Why now (this cycle, not Stage 2 proper):** Stage 2 is ambient
infrastructure (scheduled passes, Contemplator wandering, time-aware
prompting). These six are the things that have to exist _for that
infrastructure to feel ambient_. Order matters — building scheduled
Contemplator passes against a brain with no Tier 3 types or no Claude Code
context is wasted work.

**Acceptance for the cycle as a whole (when it eventually closes):**

- Tier 3 brain types: tables exist, helpers shipped, prompts updated, but
  not necessarily _exercised_ yet (that's Stage 2's job)
- Local read cache: Helm degrades gracefully on Supabase outage; a runbook
  documents the failure mode
- Claude Code bridge: at minimum, project-level summary writes from Claude
  Code sessions land in Helm's brain (full bidirectional may wait)
- PWA: installable on mobile, push permission requested
- Push path: end-to-end test sends a notification triggered by a
  `helm_curiosity` status change
- Voice spike: ADR landed, decision recorded (build / wait / never)

---

## Open findings — surfaced during T1, deferred

### Finding #003 — Repo lacks root .gitignore

**Surfaced:** 2026-04-25, PR for T0.A2 (pre-commit hooks).
**Owner:** TBD (small `chore(repo)` PR, Batch tier).
**Reference:** Only `helm-ui/.gitignore` exists. Root has none.
**Proposal:** Add a root `.gitignore` covering: `node_modules/`, `__pycache__/`,
`*.pyc`, `.venv/`, `.cache/`, `supabase/.temp/`, `.vite/`, `dist/`, `*.log`,
editor temps, OS turds (`.DS_Store`, `Thumbs.db`). Keep helm-ui's existing
`.gitignore` for its frontend-specific exclusions.
**Why now / why not now:** T0.A2's `git status` listed six untracked junk
paths (`$TMPFILE`, `helm-ui/.vite/`, `services/helm-runtime/__pycache__/`,
`services/helm-runtime/agents/__pycache__/`, `supabase/.temp/`, root
`node_modules/.cache/` from a hook side-effect). None should ever be
tracked. Excluded from T0.A2's scope to keep the PR surgical (T0.A2 is "5
named hooks," nothing more). One small PR resolves it.
**Acceptance:** `git status --short` on a clean checkout shows no junk.
The six paths above are silently ignored.

---

To add a finding, append a `### Finding #NNN — title` block. SITREPs in
`docs/stage1/SITREPs/` can reference the finding number for cross-linking.
Block structure:

```
### Finding #NNN — title
**Surfaced:** date / PR #
**Owner:** TBD
**Reference:** (relevant founding doc or spec section)
**Proposal:** (what to do)
**Why now / why not now:** (the deferral reasoning)
**Acceptance:** (how we'll know it's done)
```

---

## Resolved

### Finding #001 — Brain object types Tier 2 expansion → pulled into T1 as T0.B7

**Surfaced:** 2026-04-24, during V2 spec architecture review.
**Resolved:** 2026-04-24 — pulled into T1 as task T0.B7, before T1 execution
started. Decision recorded in V2 spec Appendix C.5.
**Reference:** `docs/founding_docs/Helm_Brain_Object_Types.md` §Tier 2,
V2 spec §T0.B7.

**Original proposal:** Implement the three Tier 2 brain object types
(`helm_curiosities`, `helm_promises`, `helm_entities` deepening) as the
first post-T1 work cycle.

**Why pulled into T1:** Two reasons made the deferral cost higher than the
inclusion cost:

1. **Cost of return.** T0.B1 (memory module abstraction) and T0.B6 (agent
   prompt rewrite) leave the memory layer fresh in everyone's head.
   Coming back weeks later to add three more types means re-paging in the
   abstraction, the agent prompts, and the test surface. Doing it
   immediately (T0.B7) is genuinely cheaper.
2. **Hello-world depth.** T3.5 is the first laptop hello-world. Without
   Tier 2, Helm responds well but doesn't drive ("I'm wondering about X")
   or follow through ("I said I'd watch for Y"). With Tier 2, the first
   hello-world meaningfully exercises Helm's ambient cognition.

**Trade-off accepted:** PR count grows from 49–57 to 54–62. Tier 3 work
becomes the first post-T1 cycle (or whatever findings have accumulated by
T4.5).

**How T0.B7 is structured (see V2 spec for full detail):**

- T0.B7a: `helm_entities` deepening (smallest, sets the template)
- T0.B7b: `helm_curiosities` (first new type, end-to-end pattern)
- T0.B7c: `helm_promises` (second new type, proves pattern holds)
- ARCH-tier; STOP gate after the third sub-PR.

---

## Maintenance notes

- **Numbering:** Finding IDs are sequential and never reused. Resolved
  findings keep their original number when archived.
- **At T4.5 (T1 close SITREP):** The SITREP enumerates open findings and
  re-sorts them into either §First batch (immediate post-T1) or §Open
  (deferred to Stage 2 planning).
- **At Stage 2 planning:** This doc is reviewed alongside the brain types
  roadmap to scope the first post-T1 cycle.
- **Pointers:** New findings that are architectural (e.g., new brain types,
  new module shapes) should also be reflected in
  `docs/founding_docs/Helm_Brain_Object_Types.md` or the relevant founding
  doc. This file is the queue; the founding docs are the canonical
  reference.
