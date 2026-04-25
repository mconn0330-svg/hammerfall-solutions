# Post-T1 Findings — Queue

| | |
|---|---|
| **Status** | 🟢 Living document |
| **Created** | 2026-04-24 |
| **Purpose** | Capture findings, deferrals, and "we noticed this during T1 and chose not to do it now" items so they are not lost between T1 close and Stage 2 planning. |
| **Lifecycle** | Append during T1 PRs. Re-sort at T4.5 (T1 close SITREP). First batch is addressed immediately after T1 close — *before* Stage 2 planning kicks off. |
| **Related** | `docs/founding_docs/Helm_Brain_Object_Types.md` (architectural reference for brain-type findings), `docs/stage1/Helm_T1_Launch_Spec_V2.md` (the spec these findings sit alongside) |

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

These items are queued for the first post-T1 work cycle. Maxwell's standing
direction (2026-04-24): brain types Tier 2 expansion is **the first thing** we
address after T1 closes, alongside any other findings accumulated during T1.

### Finding #001 — Brain object types Tier 2 expansion

**Surfaced:** 2026-04-24, during V2 spec architecture review.
**Owner:** TBD post-T1.
**Reference:** `docs/founding_docs/Helm_Brain_Object_Types.md` §Tier 2.

**Proposal:** Implement the three Tier 2 brain object types:

1. **`helm_curiosities`** — open questions Helm has formed but not yet
   answered. Lets Helm carry forward unresolved threads instead of dropping
   them. Schema sketch in the brain types roadmap doc.

2. **`helm_promises`** — commitments Helm has made to the user (e.g., "I'll
   check back on X tomorrow"). Lets Helm follow through across sessions
   without Maxwell having to re-prompt. Schema sketch in the roadmap doc.

3. **`helm_entities` deepening** — current `helm_entities` is a shallow
   ENTITY MemoryType row. Tier 2 deepens it into a proper entity model with
   `entity_type` (CHECK constraint), `aliases` (text[]), `attributes` (JSONB),
   `first_mentioned_at`, `last_mentioned_at`, `salience_decay`, plus a new
   `helm_entity_relationships` table for typed relationships between entities.

**Why now (immediately post-T1, not in T1):** These types materially deepen
Helm's coherence (curiosity carryover, promise-keeping, entity-rich
conversation), but they require T0.B1's memory module to land first so they
can be added *additively* rather than surgically. The V2 T0.B1 spec is
already designed to accommodate this — see the forward-pointer in T0.B1 to
the brain types roadmap doc, which constrains the abstraction so adding
these three is a migration + enum extension + helper add, not a refactor.

**Why not in T1:** T1's job is to land the runtime + UI + brain
infrastructure that everything else builds on. Adding three new object types
inside T1 scope would (a) blow the PR count past the 49–57 budget, (b)
extend the dual-write / outbox / read-helper test surface significantly, and
(c) couple the cognitive deepening to runtime-stabilization risk. Cleaner to
ship T1, prove the memory module's extensibility by *using it* to add these
three immediately after, and let any T1-discovered abstraction issues
inform the design.

**Acceptance for this finding (when it eventually ships):**
- All three types have migrations and pass `T0.A9` migration safety checks
- `MemoryType` enum extended; existing helpers cover new types without
  changes (validates the abstraction)
- Helm prompts updated with write/read instructions for each type
- Roadmap doc updated to move these from Tier 2 to Tier 1 (or "shipped")

---

## Open findings — surfaced during T1, deferred

*(Empty at creation. T1 PRs append here.)*

To add a finding, append a `### Finding #NNN — title` block with the same
structure as Finding #001. SITREPs in `docs/stage1/SITREPs/` can reference
the finding number for cross-linking.

---

## Resolved

*(Empty at creation. Findings move here once addressed.)*

---

## Maintenance notes

- **Numbering:** Finding IDs are sequential and never reused. Resolved
  findings keep their original number when archived.
- **At T4.5 (T1 close SITREP):** The SITREP enumerates open findings, calls
  out which the first-batch cycle will tackle, and confirms the brain types
  Tier 2 expansion (Finding #001) is the lead item.
- **At Stage 2 planning:** This doc is reviewed alongside the brain types
  roadmap to scope the first post-T1 cycle.
- **Pointers:** New findings that are architectural (e.g., new brain types,
  new module shapes) should also be reflected in
  `docs/founding_docs/Helm_Brain_Object_Types.md` or the relevant founding
  doc. This file is the queue; the founding docs are the canonical
  reference.
