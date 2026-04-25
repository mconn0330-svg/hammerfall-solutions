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

*(Empty as of 2026-04-24. The original Finding #001 was pulled into T1
itself as task T0.B7 — see §Resolved below. T1 PRs append new findings to
§Open below as they surface; at T4.5 the SITREP re-sorts open findings
into either this section or the open queue for Stage 2 planning.)*

---

## Open findings — surfaced during T1, deferred

*(Empty at creation. T1 PRs append here.)*

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
