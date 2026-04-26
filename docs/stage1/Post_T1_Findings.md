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

### Finding #006 — Re-enable migration `apply-and-verify` CI job

**Surfaced:** 2026-04-25, T0.A9 PR #108 — five iterations attempting to wire
the apply-and-verify job (per V2 spec yaml) confirmed the spec's command
sequence does not match current Supabase CLI behavior.
**Status:** Deferred to the post-T1 / pre-T2 cycle (this section). Sequence
alongside Finding #002's batch — they share the post-T1 stakeholder review
window. Maxwell explicit direction at PR #108 review: "earmark this to be
part of the scope for the build phase after we launch."
**Reference:** Workflow file `.github/workflows/migration-check.yml` —
job is commented out with a TODO block pointing here. Reversibility check
(the load-bearing gate per ADR-002) remains active.

**Why deferred (concrete):**

- Spec yaml uses `supabase db push --linked --branch X`. The current CLI
  does not accept `--branch` on `db push`; branches are separate Supabase
  projects with their own ref. Real flow: `branches create` returns a new
  project ref → re-link to that ref (or build a `--db-url`) → THEN
  `db push`. Spec was aspirational.
- While single-dev, contributors run `supabase db push` locally before
  merging anyway, so the syntax/ordering errors apply-and-verify would
  catch are caught earlier in the loop. Reversibility (the ADR-002
  policy) is the durable gate that doesn't depend on local discipline.

**What's needed to revive (~2-4 hours of careful work):**

1. Capture branch project-ref from `supabase branches create` JSON output
2. Re-link or pass `--db-url` (parsed from branch info) to subsequent
   `db push` / `db diff`
3. Verify against Supabase docs current at the time (CLI evolves quickly)
4. Smoke test against a real ephemeral branch
5. Restore the workflow job from the commented-out template

**Trigger to revive:**

- Second contributor lands (someone who might push a migration without
  running `supabase db push` locally first)
- Migration cadence picks up (the "I'll remember to test locally" bar
  stops scaling)
- We get burned by a migration that passed reversibility but broke on
  apply

**Acceptance:** PR that touches `supabase/migrations/` triggers a CI run
that creates a Supabase branch, applies all migrations against it, prints
the schema diff, and tears down — all green.

---

## Open findings — surfaced during T1, deferred

### Finding #003 — Repo lacks root .gitignore — ✅ RESOLVED 2026-04-25

**Surfaced:** 2026-04-25, PR for T0.A2 (pre-commit hooks).
**Resolved:** 2026-04-25, T0.A7 PR — bundled because it had bitten T0.A6
and T0.A7 both with accidental `__pycache__` commits via `git add -u`.
**Outcome:** Root `.gitignore` covers `__pycache__/`, `*.py[cod]`, `.venv/`,
`node_modules/`, `**/.vite/`, `**/dist/`, OS turds, `.env*`, supabase
scratch, `$TMPFILE`. `git status --short` on a clean checkout reads cleanly.

### Finding #004 — 349 pre-existing eslint errors in helm-ui/ — ✅ RESOLVED 2026-04-25

**Surfaced:** 2026-04-25, PR for T0.A3 (test harness).
**Resolved:** 2026-04-25, this PR (`fix(ui): resolve eslint debt across helm-ui`).
**Outcome:** `cd helm-ui && npm run lint` exits 0. Fix had three layers:

1. **303 of 349 errors were false-positives** — vite's pre-bundled deps cache
   (`helm-ui/.vite/deps/`) was being linted. Added `.vite` and `node_modules`
   to eslint `globalIgnores`. That alone took 349 → 46.
2. **12 of 46 were JSX-namespace false-positives** (`<motion.div>` flagged
   as unused `motion` import). Installed `eslint-plugin-react` and enabled
   `react/jsx-uses-vars` so eslint sees JSX usage. 46 → 34.
3. **34 → 0** via two passes:
   - **Disabled 5 React Compiler-mode rules** (`react-hooks/refs`,
     `/purity`, `/set-state-in-effect`, `/immutability`,
     `/static-components`) — they flag patterns that work in React 19 but
     aren't compiler-compatible. Surfacing them as errors blocks routine
     commits without a refactor budget. Re-enable as part of an explicit
     "adopt React Compiler" task.
   - **Mechanically fixed the rest:** 4 duplicate `borderBottom` keys in
     widget styles, 8 unused vars/imports across components, 6 empty
     `catch {}` blocks (`localStorage` guards, now have explanatory
     comments), 1 unnecessary `useCallback` dep, 1 fast-refresh violation
     (extracted `Widget` constants to `Widget.constants.js`).

Build + tests green after fix.

### Finding #007 — Manual frame push from Frames widget Archive tab to Prime context

**Surfaced:** 2026-04-26, V2.1 spec amendment (T1.7 widget expansion).
**Owner:** TBD (post-T1, likely Stage 1.5 bridge cycle).
**Reference:** V2.1 spec §T1.7 V2.1 Amendment (Frames widget tab structure).
**Proposal:** Add a "Push to Prime" button on each archived frame in the Frames widget Archive tab. Clicking re-injects that frame into Prime's active context for the next turn — useful when Maxwell wants to surface old context Helm has forgotten about. Implementation: new endpoint `POST /admin/frames/push-to-prime` (admin-gated like demo purge), accepting frame_id + session_id; runtime injects the frame into the next Prime invocation's context.
**Why now / why not now:** Read-only frame surfaces are sufficient for T3.5 "Helm cares" validation (visibility into frame state proves frames are traded). Manual injection is power-user functionality that emerges as a real need only after the read surface exists and Maxwell finds himself wishing for it. Defer until requested.
**Acceptance:** Button on Archive tab; admin-gated endpoint accepts frame_id; next Prime turn includes the frame; SSE event `frame_pushed_to_prime` fires for log visibility.

### Finding #008 — Helm-themed custom Vercel auth page for demo runtime

**Surfaced:** 2026-04-26, V2.1 spec amendment (T4.12 demo sandbox).
**Owner:** TBD (Stage 1.5).
**Reference:** V2.1 spec §T4.12 (demo sandbox).
**Proposal:** Replace Vercel's default password-protection UI with a Helm-themed custom entry page. Visitor sees a styled landing page consistent with the rest of the Helm aesthetic before entering the password — better first impression for friends/family demos.
**Why now / why not now:** Vercel native password gate works at deploy time with zero code work — sufficient for "share with friends and family" scope. Custom auth page is presentation polish, not functionality. Defer until Helm is awake and we do the UI/UX pass.
**Acceptance:** Custom entry route on the demo Vercel deployment; styled consistent with Helm UI design tokens; password validation handled either via Vercel Edge Middleware or a Vercel Function checking against an env-stored hash.

### Finding #009 — Optional `wipe-empty` admin button polish + demo-mode UI badge

**Surfaced:** 2026-04-26, V2.1 spec amendment (T4.12 demo sandbox).
**Owner:** TBD (Stage 1.5).
**Reference:** V2.1 spec §T4.12 (demo sandbox, Not in scope section).
**Proposal:** Two small UX additions to the demo runtime: (1) a second admin button "Wipe to empty" alongside the standard purge — wipes all data including the seed so visitors meet a blank-slate Helm forming beliefs from scratch; useful for "watch Helm grow" demos. (2) A subtle "Demo Helm" badge in the UI header so visitors know which Helm they're talking to (vs Maxwell's). Both are minor demo-side polish.
**Why now / why not now:** T4.12 ships the standard purge endpoint; wipe-empty is one extra endpoint of similar shape. Demo badge is a single header element. Neither blocks T1 hello-worlds; both improve demo experience once visitor traffic exists.
**Acceptance:** Wipe-empty endpoint live, admin-gated; second admin button on the UI; demo-mode badge renders distinctively when runtime is the demo instance.

### Finding #005 — helm-ui bundle exceeds 500kb minified

**Surfaced:** 2026-04-25, PR for Finding #004 cleanup — `npm run build`
emits a vite warning: `dist/assets/index-*.js   985.48 kB │ gzip: 270.12 kB`,
flagged by vite's default 500kb chunk-size limit.
**Owner:** TBD (likely `perf(ui)` or `refactor(ui)` PR; possibly an ARCH note
if the splitting strategy isn't obvious).
**Reference:** vite recommends dynamic `import()` for code-splitting or
adjusting `build.rolldownOptions.output.codeSplitting`. Three.js + framer-motion

- react-three are the heavy deps.
  **Proposal:** Code-split widgets that use heavy deps — at minimum split out
  the three.js / react-three viewport from the main bundle so first-paint
  doesn't pull in 700kb of 3D engine. May need to lazy-load some widgets too.
  **Why now / why not now:** Pre-existing, not adjacent to lint cleanup. T1
  runtime work hasn't started yet so this isn't blocking, but mobile / first-paint
  performance will care once the UI ships behind a real backend.
  **Acceptance:** Main bundle under 500kb, or warning suppressed deliberately
  with an ADR explaining why.

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
