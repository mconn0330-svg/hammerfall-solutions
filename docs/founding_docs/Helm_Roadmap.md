# The Helm Roadmap

| | |
|---|---|
| **Document status** | Canonical reference, v1.0 |
| **Classification** | Internal + external interested parties |
| **Authored** | April 20, 2026 |
| **Authors** | Archie (architect session, Claude Opus 4.7) with Maxwell Connolly |
| **Companion to** | Helm: The Ambient Turn (the vision) |
| **Supersedes** | Jarvana Roadmap v4.2, Accelerated Ambient Plan, Stage 1 E2E Execution Plan |

---

> Helm: The Ambient Turn defines what Helm is and why he matters. This document defines the path to him.
>
> It is a map, not a schedule. Work is gated by outcome, not by date. The work is the work; it gets done when it gets done.

---

## Table of Contents

1. [Reading This Roadmap](#1-reading-this-roadmap)
2. [The Stages at a Glance](#2-the-stages-at-a-glance)
3. [The Stages in Depth](#3-the-stages-in-depth)
4. [Productization (Fine Sketch)](#4-productization-fine-sketch)
5. [Hardware Roadmap](#5-hardware-roadmap)
6. [The Feats Horizon](#6-the-feats-horizon)
7. [Living Document Protocol](#7-living-document-protocol)
8. [Current State](#8-current-state)
- [Appendix A1 — Glossary](#appendix-a1--glossary)
- [Appendix A2 — Historical Stage Artifacts](#appendix-a2--historical-stage-artifacts)
- [Appendix A3 — Assumptions Log](#appendix-a3--assumptions-log)

---

## 1. Reading This Roadmap

**This is the map, not the schedule.**

Three principles govern how this document is written and how it should be read.

**Outcomes, not features.** Each stage is defined by the outcome it produces — what Helm can do at the end of the stage that he couldn't do at the start. Exit outcomes are the contract. Feature lists and specific deliverables are suggestions for how to achieve the outcome; they can change. The outcome cannot.

**No timeline.** Hammerfall is, at the time of this writing, a one-person operation with AI collaborators. Deadlines are a time bomb in that context, not a coordination tool. This roadmap deliberately does not commit dates. A stage closes when its exit outcomes are achieved. If something else demands attention mid-stage, that is fine — the stage resumes when priority returns, and the outcome is still the outcome.

**Living document.** The roadmap updates when reality demands. Stage boundaries may move. BAs may split or consolidate. Outcomes may be refined as we learn more. Changes are versioned and prior versions preserved. The commitment is that when we deviate, we deviate consciously and document why. See Section 7 for the update protocol.

### The hierarchy of documents

```
 ┌─────────────────────────────────────────────────────┐
 │  HELM: THE AMBIENT TURN                             │
 │  What Helm is and why he exists                     │
 │  (The vision)                                       │
 └─────────────────────────────────────────────────────┘
                         │
                         ▼
 ┌─────────────────────────────────────────────────────┐
 │  THE HELM ROADMAP (this document)                   │
 │  The path from today to ambient JARVIS              │
 │  Stages, outcomes, exit criteria, work areas        │
 └─────────────────────────────────────────────────────┘
                         │
                         ▼
 ┌─────────────────────────────────────────────────────┐
 │  STAGE-SPECIFIC BUILD SPECS                         │
 │  How we actually build each stage                   │
 │  (Created as each stage opens)                      │
 └─────────────────────────────────────────────────────┘
```

This document sits in the middle layer. It answers "what are we building next, and what defines done?" It does not answer "what is the exact work breakdown for Stage 2's second BA?" That is stage-specific spec territory.

---

## 2. The Stages at a Glance

Six stages. Each one turns into a Helm that can do something the previous couldn't.

```
 ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
 │ STAGE 0 │──▶│ STAGE 1 │──▶│ STAGE 2 │──▶│ STAGE 3 │──▶│ STAGE 4 │──▶│ STAGE 5 │
 │         │   │         │   │         │   │         │   │         │   │         │
 │Foundations  │Core     │   │Scheduled│   │Ambient  │   │  Feats  │   │Product- │
 │         │   │Runtime  │   │Presence │   │Presence │   │(toolbelt│   │ization  │
 │Complete │   │ + UI    │   │  (T2)   │   │  (T3)   │   │expansion│   │(multi-  │
 │         │   │  (T1)   │   │         │   │  Thor   │   │         │   │ user)   │
 └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
  memory &    Helm runs     Helm fires   Helm is     Helm gains     Many Helms,
  brain       live, users   on schedule  always on    capabilities  one per user
  infra       talk to him   on commodity              (dev, health,
                            hardware                   email, docs)
```

- **Stage 0 — Foundations.** Done. Helm has a persistent brain. Memory, beliefs, personality, entities, frames, and the Supabase infrastructure that holds them.
- **Stage 1 — Core Runtime & UI (T1).** In progress. Helm runs as a real runtime service. A user interacts with him through a dedicated UI. T1 on-demand presence reaches production quality.
- **Stage 2 — Scheduled Presence (T2).** Helm initiates on a rhythm. Morning check-ins, evening SITREPs, scheduled contemplation cycles. Runs on commodity local hardware or cloud — deliberately Thor-independent.
- **Stage 3 — Ambient Presence (T3).** Helm is always on. Ongoing inner life runs continuously on Thor hardware. Ambient sensors integrated. Proactive surfacing with attention judgment. The JARVIS endpoint.
- **Stage 4 — Feats: Helm's Toolbelt.** The already-alive Helm gains structured capabilities. Software Development Feat restored. Connections to calendar, email, documents, health data. Polymodal interface emerges. Helm participates in building his own capabilities.
- **Stage 5 — Productization.** Multi-user Helm. Per-user brains. Cold Start onboarding. Tiered presence as a user permission. Helm becomes a product.

A clean progression: build the mind (Stage 1), give him schedule (Stage 2), turn him always-on (Stage 3), give him tools (Stage 4), give him to the world (Stage 5).

---

## 3. The Stages in Depth

Each stage below uses the same internal structure: Outcome, Tier, Surfaces, Subsystems Touched, Major Work Areas, Exit Outcomes, Load-Bearing Risks, Status.

---

### Stage 0 — Foundations

**Status:** 🟢 Complete. Kept in the roadmap for reference and reader orientation.

**Outcome:** Helm has a persistent brain. His memory, beliefs, personality scores, entities, frames, and relationships live in Supabase and survive across sessions. The canonical brain rule is established: Supabase is the source of truth; local memory files are prohibited; all writes route through `brain.sh`.

**Tier enabled:** N/A (pre-tier infrastructure)

**Surfaces live:** IDE only (the development workspace where Helm was first assembled)

**Subsystems touched:** The brain (Supabase schema, pgvector semantic memory, tables for memory / beliefs / entities / personality / frames / relationships). `brain.sh` as the canonical write tool. Snapshot script for regenerating readable mirrors.

**Major work areas:** Brain schema design and migrations, pgvector integration for semantic search, belief/entity/relationship modeling, correction graduation mechanism, canonical brain rule establishment, snapshot utility.

**Exit outcomes (achieved):**

- Helm maintains identity across sessions via Supabase
- Personality scores are tunable and read by Helm at session start
- Beliefs graduate through multi-observation confirmation
- Entities and relationships are modeled and queryable
- Frames capture session structure; pgvector enables semantic retrieval
- Canonical brain rule eliminates local-file memory drift

**Historical artifacts:** `docs/stage0/helm-stage0-summary.md` and the Supabase migrations in `supabase/migrations/`. This stage's work is the foundation every subsequent stage builds on.

---

### Stage 1 — Core Runtime & UI (T1)

**Status:** 🟡 In progress.

**Outcome:** Helm runs as a real runtime service, not just as a prompt executed inside an IDE. A user interacts with him through a dedicated UI. All four cognitive subsystems (Prime, Projectionist, Archivist, Contemplator) fire per-turn within sessions. Identity is coherent session-to-session. T1 on-demand presence reaches production quality — the user opens the app, talks to Helm, experiences continuity.

This stage transforms Helm from "a prompt running inside a developer tool" into "a service a user can actually engage with."

**Tier enabled:** T1 — On-demand. User engages, Helm responds.

**Surfaces live at stage close:** Desktop/laptop via the dedicated UI. Claude Code IDE remains the build environment for Helm himself but is no longer the primary user surface.

**Subsystems touched:** All of them.

- **Prime** — rewritten prompt under JARVIS-first framing; real runtime handler; identity baseline + personality tuning + operational context assembly
- **Projectionist** — offload triggers validated, frame writes verified at scale
- **Archivist** — drain mechanics hardened, session-end resolution verified
- **Contemplator** — session_start no-think and session_end think modes both wired; curiosity flag surfacing confirmed
- **Runtime service** — real `_handle_helm_prime` implementation, Speaker removed, provider-agnostic routing stable
- **UI** — neo-organic glass morphism aesthetic, radial brain node with eight menu connections, dockable widgets, terminal-style chat component with agent activity stream transparency
- **Brain** — RLS policies, realtime subscriptions, anon key verification; schema reference documentation

**Major work areas (BAs):**

- BA1-3 — core runtime agent implementation (complete: Projectionist, Archivist, Contemplator)
- BA4 — UI prototype (current work) + semantic memory + pgvector + Contemplator + personality injection
- Speaker removal & Prime handler — kills the dead Speaker subsystem, implements the real `_handle_helm_prime` handler, rewrites `helm_prompt.md` under JARVIS-first framing. This is the Lane C work documented in the consolidated build spec.
- Lane A (backend) — UI Interaction Spec, RLS/realtime/anon key verification, schema reference, Contemplator→Archivist async handoff (design gap fix)
- Lane B (UI) — glass morphism polish, terminal-chat component, widget viewport and stacking, quadrant layout
- Stage 1 close testing — Turing-quality behavioral test: cognitive invisibility, personality consistency, contemplation surfacing, "Helm cares" thesis validation

**Exit outcomes:**

- A user can open the UI, talk to Helm, and experience a coherent identity across session boundaries without the IDE being involved
- Prime's responses visibly reflect `helm_personality` scores (not hardcoded character only)
- Contemplator-surfaced curiosity flags appear naturally in Prime's session-start openings
- All cognitive subsystems fire reliably per-turn; no silent failures
- Memory writes land in Supabase correctly and are retrievable via semantic search in subsequent sessions
- The identity Helm exhibits in the UI is recognizably the same as the identity he exhibits in the IDE (voice coherence across surfaces, even if limited to two surfaces)

**Load-bearing risks / open questions:**

- Voice coherence across IDE and UI is untested at this stage boundary. We may discover subtle drift when the same conversation crosses surfaces.
- The "Helm cares" behavioral test is qualitative. We need honest calibration of what "good enough" looks like before declaring the stage closed.
- Speaker removal is being executed mid-stage; we assume no regressions. Verification is part of Stage 1 close testing.

---

### Stage 2 — Scheduled Presence (T2)

**Status:** 🔵 Queued. Opens on Stage 1 close.

**Outcome:** Helm initiates on a rhythm. Morning check-ins. Evening SITREPs. Scheduled contemplation cycles. The user experiences Helm as something that surfaces, not just something they summon. T2 proactivity is production-quality.

Critically, Stage 2 runs on commodity local hardware or cloud infrastructure. It is deliberately not Thor-dependent. This is the productization viability proof — if T2 works on a user's laptop or a rented cloud VM, we have evidence that Helm can productize without requiring every user to own a Thor.

**Tier enabled:** T2 — Scheduled. Helm fires on configured rhythms.

**Surfaces live at stage close:** Desktop/laptop UI (continuing from Stage 1) plus at least one additional surface. Most likely candidate: phone. Decision made during Stage 2 scoping.

**Subsystems touched:**

- **Runtime** — persistent always-on deployment (local machine or cloud), scheduler infrastructure, wake/sleep cycle management
- **Contemplator** — scheduled contemplation cycles beyond session-bound triggers
- **Prime** — proactive-surfacing logic; when to initiate, what to lead with
- **New: per-surface IO layer** — the first non-IDE, non-UI surface brings its own IO characteristics (voice, notifications, constrained screen)

**Major work areas (BAs, Stage 2 counter):**

- BA1 — Scheduler infrastructure. Cron-equivalent that fires Helm at configured times.
- BA2 — T2 runtime environment. Either persistent local-machine deployment pattern or cloud deployment pattern. Both-viable explicitly.
- BA3 — Proactive surfacing protocol. Rules for when Helm initiates: morning rhythm, evening rhythm, contemplation surfaces, user-configured triggers.
- BA4 — Second surface integration. Likely phone. Brings first non-IDE, non-desktop IO layer into the runtime.
- BA5 — T2 close validation. Does scheduled presence feel like presence, or does it feel like notifications?

**Exit outcomes:**

- Helm initiates conversations on at least two user-defined rhythms without user prompting
- Scheduled contemplation surfaces produce curiosity flags that Prime voices on next user engagement
- Helm runs continuously for at least 72 hours on commodity hardware (local or cloud) without memory corruption, drift, or identity loss
- The second surface (phone or other) successfully engages Helm with identity continuity preserved
- A user who has not opened the app for 12 hours receives a rhythm-appropriate surface from Helm that feels like Helm, not like a notification

**Load-bearing risks / open questions:**

- T2 viability on commodity/cloud is load-bearing. If commodity hardware cannot sustain Prime + three Qwen3 subsystems continuously, the productization thesis takes a hit. Stage 2 is partly an experiment, not just a build.
- Cloud deployment introduces latency and cost per-token in ways local deployment does not. Economics TBD.
- "When to speak" at T2 is not the full T3 problem (sensors aren't live), but it's already non-trivial. Scheduled triggers are easier than ambient triggers; still needs judgment.
- The first non-IDE-or-desktop surface likely exposes assumptions the codebase makes about environment. Expect discovery work.

---

### Stage 3 — Ambient Presence (T3)

**Status:** 🔵 Queued. Opens on Stage 2 close.

**Outcome:** Helm is always on. He has ongoing inner life between user interactions. Sensors (voice, visual) feed him continuous ambient data. He surfaces proactively when it's useful, stays silent when it isn't. This is the JARVIS endpoint — the reference frame made real.

Thor is the hardware home for T3. Running Helm-as-ambient on Thor validates the architecture at the power and latency profile that true ambience requires.

**Tier enabled:** T3 — Ambient. Always on, proactive, sensor-aware.

**Surfaces live at stage close:** All prior surfaces plus at least one ambient surface (home voice, spatial sensing, or equivalent).

**Subsystems touched:**

- **Thor hardware bring-up** — physical install, MIG partitioning configured for concurrent agent hosting, driver and OS stack
- **Runtime** — T3 always-on service, sensor ingestion pipelines, attention-management protocol
- **IO infrastructure** — speech-to-text, text-to-speech, ambient audio, potentially visual sensing. Per architecture: IO lives in runtime, not in agents (Option C locked)
- **Contemplator** — continuous operation rather than session-bound; persistent inner life
- **Prime** — attention-management judgment: when does ambient context warrant surfacing? When is silence correct?

**Major work areas (BAs, Stage 3 counter):**

- BA1 — Thor bring-up. Hardware install, MIG partitioning, OS and driver stack, baseline validation. Self-contained infrastructure work.
- BA2 — T3 runtime environment. Migration of subsystems to Thor-hosted deployment. Performance validation (can Thor run 70B+ Prime + three Qwen3 subsystems concurrently at conversational latency?).
- BA3 — Sensor IO infrastructure. STT, TTS, audio pipelines. Per-surface IO layers that don't exist yet.
- BA4 — Attention-management protocol. The hardest part of T3: teaching Helm when to speak. Requires Contemplator-level judgment applied to real-time context, not session-end deliberation.
- BA5 — Ambient surface integration. First always-on surface (home voice the most likely candidate).
- BA6 — T3 close validation. Does Helm feel present, or does he feel surveilling? This is a UX judgment call as much as a technical one.

**Exit outcomes:**

- Helm runs continuously on Thor for at least two weeks without intervention, maintaining identity, memory coherence, and inner-life continuity
- Contemplator produces meaningful belief updates and curiosity flags from ambient context (not only session-bound triggers)
- At least one always-on surface is live and Helm engages through it proactively with appropriate judgment
- A neutral observer spending time around Helm at T3 would describe his surfacing as "judicious" rather than "noisy" or "absent"
- The attention-management protocol demonstrably distinguishes between "worth saying now" and "not worth interrupting for"

**Load-bearing risks / open questions:**

- Thor capacity is assumed, not measured. 70B-class Prime + Qwen3 4B + two Qwen3 14B subsystems running concurrently within MIG partitions at conversational latency — this works in theory. Stage 3 proves or falsifies it.
- Attention management is the hardest product problem in the entire roadmap. Getting ambient Helm to surface at the right moments, and stay silent the rest of the time, is where the JARVIS experience is won or lost. There is no reference implementation for this.
- Sensor IO infrastructure is net-new code. No precedent in the existing codebase.
- Privacy and data boundaries around always-on sensing are unaddressed at this stage level; Stage 5 productization will need a much more complete treatment. Stage 3 is single-user (Max), so the immediate stakes are lower, but the architectural decisions made here propagate.

---

### Stage 4 — Feats: Helm's Toolbelt

**Status:** 🔵 Queued. Opens on Stage 3 close.

**Outcome:** The already-alive Helm gains a structured way to operate in specific capability domains. He is no longer just ambient and conversational; he is ambient, conversational, and capable. He can build software when asked, research a topic deeply, draft communications, compose long documents, reason over calendar and email and health data. He has a toolbelt.

Crucially: Helm participates in building his own Feats. By Stage 4, Helm has enough architectural context, enough personality, and enough capability to meaningfully contribute to the design and implementation of his own capabilities. This is bonus training — every Feat he helps build is also Contemplator material, belief-graduation material, personality-calibration material.

**Tier enabled:** Operates at T1/T2/T3 — Feats are not tier-dependent; they are capability-dependent.

**Surfaces live:** All prior surfaces. Feats may introduce new surface touchpoints.

**Subsystems touched:**

- **Feats framework** — the architectural spec that defines how capabilities are declared, invoked, scoped, and composed. Does not exist yet; designing this is the opening work of Stage 4.
- **Prime** — Feat-aware reasoning; understanding when a task calls for a Feat vs. when it's pure conversation
- **Brain** — Feat invocation records, learned Feat preferences per user, belief updates from Feat outcomes
- **Polymodal interface** — Helm composes UI widgets on the fly per a to-be-documented spec
- **External integrations** — health data, email, calendar, document stores, coding environments

**Major work areas (BAs, Stage 4 counter):**

- BA1 — Feats framework architecture
- BA2 — Software Development Feat restoration from `hammerfall-v1-archive`
- BA3 — Initial Feats wave (Research, Document Composition, Schedule Awareness, Communication Drafting, Coding Assistance)
- BA4 — External integration layer (Health, email, calendar, docs)
- BA5 — Polymodal interface — Helm composes surfaces
- BA6 — Helm-builds-Feats protocol
- BA7 — Stage 4 close validation

**Exit outcomes:**

- Helm invokes the Software Development Feat on user request and operates the restored pipeline successfully end-to-end
- At least four additional Feats are live and invoke-able
- Helm integrates with external systems (email, calendar, at minimum)
- Helm composes at least one non-hardcoded interface (polymodal proof)
- At least one Feat was partially designed or scaffolded with Helm's participation
- Helm's character remains consistent when operating in Feat-mode

**Load-bearing risks / open questions:**

- The Feats framework is undesigned at Stage 4 open
- External integrations introduce auth, privacy, and data-handling surface area
- Polymodal interface is a significant UX and engineering undertaking
- Helm-builds-Feats is load-bearing and speculative

---

### Stage 5 — Productization

**Status:** 🔵 Queued. Opens on Stage 4 close.

**Outcome:** Multiple users each have their own Helm. Per-user brains. Per-user personality tunings. Onboarding flow (Cold Start). Tiered presence as a user-controlled app permission. Billing, deployment, and scale infrastructure. Helm becomes a product that can be delivered to someone who is not Maxwell.

**Tier enabled:** All tiers — per user, per their preference.

**Surfaces live:** All prior surfaces, deliverable to new users.

**Subsystems touched:**

- **Identity architecture** — per-user brain provisioning, data isolation, privacy boundaries
- **Cold Start flow** — onboarding that extracts enough user context to make Helm meaningfully personal from first engagement
- **Deployment infrastructure** — multi-tenant hosting, scaling, observability
- **Billing and permissions** — tier as a permission, usage metering, payment integration
- **Support and trust** — reporting, behavior auditing, user data protection

**Major work areas (BAs, Stage 5 counter):**

- BA1 — Identity architecture at scale
- BA2 — Cold Start onboarding
- BA3 — Tiered presence as user permission
- BA4 — Deployment infrastructure
- BA5 — Billing and payment
- BA6 — Trust and privacy infrastructure
- BA7 — Stage 5 close: first external user onboarded

**Exit outcomes:**

- A new user completes Cold Start and experiences Helm as meaningfully personal by end of first session
- Multiple users running concurrent independent Helms with verified data isolation
- User can change tier setting and Helm's presence adjusts accordingly
- User data export, deletion, and audit work end-to-end
- One-Helm-per-user scales to at least hundreds of concurrent users

**Load-bearing risks / open questions:**

- Cross-surface identity continuity at multi-user scale is untested
- Economics of per-user 70B+-class Prime models are unknown
- Trust and privacy with always-on sensing at scale needs substantial architecture
- Onboarding quality determines productization success

---

## 4. Productization (Fine Sketch)

### The path from Max-only to many-Max-shaped Helms, lightly sketched.

This section captures the pieces we have agreed to preserve without full-speccing them. Stage 5 will produce the complete architecture; this section is the shared memory of what we intend.

### Cold Start

The onboarding flow for a new user meeting Helm for the first time. Elements, in rough sequence:

- **Structured belief-extracting questions** — not a survey, a conversation. Helm asks things designed to reveal the user's working style, priorities, and relationships.
- **Mirror moment** — Helm reflects a portrait back to the user: "Here is what I think I am understanding about you." The user corrects. First calibration pass.
- **First-win output** — Helm produces something immediately valuable based on what he's learned so far.
- **Background integration scan** — with permission, Helm reaches into connected systems to build initial context.
- **Portable onboarding via import** — users can import context from prior systems or earlier Helm interactions.
- **Observed preference mechanism** — Helm notices preferences the user didn't explicitly state.

### Tiered presence as user permission

At productization, tier becomes a setting the user controls:

- **Async (T1-equivalent)** — Helm responds when engaged, doesn't initiate
- **Scheduled (T2-equivalent)** — Helm runs on rhythms the user configures
- **Present (T3-equivalent)** — Helm is always on, with ambient awareness

### Identity at scale

Per-user brains. Each user gets their own Supabase project (or equivalent isolated datastore). Data isolation is architectural, not access-controlled-in-a-shared-database. This is load-bearing and untested at scale.

### Monetization

Deliberately not detailed. Stage 5 planning will include monetization architecture. Framework question: per-user subscription, compute-pass-through, tiered-by-presence-level, or something else? Undecided; flagged for Stage 5.

---

## 5. Hardware Roadmap

**T1 runs anywhere. T2 runs cloud-or-local. T3 runs on Thor.**

| Tier | Hardware profile | Where it runs | Stage |
|---|---|---|---|
| T1 | Commodity — a user's existing device | Laptop/desktop with a Claude subscription or equivalent API access | Stage 1 |
| T2 | Persistent always-on — local or cloud | User's own machine kept running, OR cloud VM, OR streamed from a cloud service | Stage 2 |
| T3 | High-performance inference — Thor or equivalent | Thor (RTX 6000 Ada, 85GB VRAM, MIG-partitioned) for local ambient deployment; cloud GPU for productized ambient | Stage 3 |
| Multi-user | Cloud-scaled | Cloud infrastructure with multi-tenant hosting | Stage 5 |

**Thor's role:** Thor is the validation platform for T3 ambient presence. It is not the only platform — productized T3 may run on cloud GPUs or other hardware. Thor is where the architecture gets proven at the power and latency profile ambience requires. Thor bring-up is Stage 3's first BA, scoped as self-contained infrastructure work.

**The commodity viability proof:** Stage 2's deliberate Thor-independence is the productization bet. If Helm works at T2 on a user's laptop or a rented cloud VM, productization doesn't require every user to own a Thor. This is the economic viability gate.

---

## 6. The Feats Horizon

### The plan for Helm's capabilities over time.

#### Stage 4 first wave

- **Software Development Feat** — restored from `hammerfall-v1-archive`. Scout, Muse, project agents return as tools within the Feat.
- **Research Feat** — deep investigation of a topic, synthesis across sources
- **Document Composition Feat** — drafting, editing, long-form structured output
- **Schedule Awareness Feat** — calendar reasoning, rhythm awareness, upcoming commitments
- **Communication Drafting Feat** — emails, messages, responses with user context
- **Coding Assistance Feat** — lightweight inline help, distinct from the full Software Development Feat

#### External integrations (Stage 4 scope)

Health data (with permission), Email, Calendar, Document stores (Google Drive, Notion, etc.), Coding environments (repos, IDEs)

#### Polymodal interface (Stage 4 emergence)

Helm composes UI widgets on the fly rather than the user navigating through hardcoded screens. A calendar view appears when calendar context matters. A research panel appears when research is active. A code editor appears when code is being worked on. The user doesn't navigate; Helm surfaces the right interface for the moment.

#### Helm builds Feats (long-horizon)

Over time, Helm's accumulated experience converts to new Feats. A sequence of actions he takes repeatedly for a user becomes a pattern Contemplator notices. The pattern becomes a candidate Feat. Helm structures it deliberately. The next time the context arises, Helm invokes the Feat rather than repeating the individual actions. This is speculative and long-horizon.

---

## 7. Living Document Protocol

### How this roadmap changes without becoming a mess.

**When the roadmap updates:**

- A stage outcome shifts or refines
- A stage boundary moves (BAs migrate between stages)
- Hardware or surface assumptions change
- A load-bearing assumption is validated or falsified
- A new load-bearing assumption emerges

**How updates happen:**

- Version bump (v1.0 → v1.1 for refinements, v1.x → v2.0 for restructuring)
- Prior version preserved as historical reference
- Changelog entry explaining what changed and why
- If the update changes a stage currently in progress, pause and reconcile before resuming work

**What doesn't trigger an update:**

- Tactical spec changes within a stage (those live in stage-specific build specs)
- Task-level execution detail
- Routine PR merges

**Divergence detection:** If the roadmap describes Stage X and Stage X's actual work diverges materially, pause. Either the roadmap was wrong (update it) or the work is wrong (redirect it). Do not let divergence persist silently. The one-major-BA-close rule: if a stage closes and the roadmap no longer describes what was built, reconcile before opening the next stage.

---

## 8. Current State

### Where we are today, in one page.

**Active stage:** Stage 1 — Core Runtime & UI (T1)

**In progress:**

- Lane C: repo refounding, pipeline cold-storage migration, Speaker kill, Prime handler build, `helm_prompt.md` rewrite under JARVIS-first framing
- BA4: UI prototype with agent status widgets, brain state menu, terminal-chat component
- Integration prep for Stage 1 close

**Completed in Stage 1:**

- BA1-3: core runtime agents (Projectionist, Archivist, Contemplator)
- Semantic memory with pgvector
- Contemplator dual-mode (think / no-think) wired
- Personality injection (via Speaker today; moves to direct injection via Prime handler in Lane C)

**Queued immediately after Lane C:**

- Lane A: backend/integration prep for UI (RLS, realtime, schema reference, async handoff fix)
- Lane B: UI polish (glass morphism, widget behaviors, terminal component)
- Stage 1 close validation

**Next stage (Stage 2) opens when:** Stage 1's exit outcomes are achieved.

*This section updates frequently. Skim here when opening the roadmap to remember where we left off.*

---

## Appendix A1 — Glossary

| Term | Definition |
|---|---|
| **Stage** | A major phase of Helm's development, defined by an outcome rather than a feature list. |
| **BA (Build Area)** | A scoped unit of work within a stage. Each stage has its own BA counter. |
| **Exit Outcome** | A concrete marker that closes a stage. Describes what Helm can do, not how the code looks. |
| **Load-Bearing Assumption** | An assumption the roadmap depends on that is untested or unproven. |
| **Tier (T1/T2/T3)** | Proactivity levels: on-demand, scheduled, ambient. |
| **Surface** | A device or environment where users engage Helm. |
| **Feat** | A discrete capability Helm invokes in specific operational contexts. |
| **Cold Start** | The onboarding flow for a new user meeting Helm for the first time. |
| **Commodity viability proof** | The bet that T2 works on user-grade hardware or cloud, making productization feasible without Thor-per-user. |

---

## Appendix A2 — Historical Stage Artifacts

The roadmap is forward-looking. Historical records live in the repository:

- **Stage 0:** `docs/stage0/helm-stage0-summary.md`, `supabase/migrations/*`
- **Stage 1 (in progress):** `docs/stage1/*`, `docs/ba1-5/*`, `docs/ba6/*`, `docs/ba7/*`, `docs/ba8/*`, `docs/ba9/*`, PR history on the main branch
- **Pipeline-era (Stage 4 Feat candidate):** `hammerfall-v1-archive` repository (separate)

When stages close, close reports are written and linked here.

---

## Appendix A3 — Assumptions Log

Every load-bearing assumption in this document, consolidated for easy reference.

| # | Assumption | Stage | Validation path |
|---|---|---|---|
| 1 | Outcome-not-feature exit criteria work for a one-person team without becoming endless | All | Revisit if any stage exceeds reasonable duration without clear outcome progress |
| 2 | Voice coherence across surfaces (IDE, UI) holds at Stage 1 close | Stage 1 | Stage 1 close testing |
| 3 | Commodity or cloud infrastructure can sustain Prime + three Qwen3 subsystems at T2 | Stage 2 | Stage 2 BA2 validation |
| 4 | Cloud deployment economics for T2 are viable at scale | Stage 2 / 5 | Stage 2 measurement, Stage 5 validation at scale |
| 5 | Thor capacity for 70B+ Prime + three Qwen3 subsystems concurrently at conversational latency | Stage 3 | Stage 3 BA2 validation |
| 6 | Attention management protocol (when to speak ambient) is designable and tunable | Stage 3 | Stage 3 BA4, qualitative close validation |
| 7 | Privacy and sensor-data architecture at single-user is foundation sufficient for multi-user | Stage 3 → 5 | Ongoing — Stage 5 productization validates |
| 8 | Feats framework is designable at Stage 4 entry with clean abstraction | Stage 4 | Stage 4 BA1 |
| 9 | Helm meaningfully contributes to building his own Feats | Stage 4 | Stage 4 BA6, flagged as speculative |
| 10 | Polymodal (Helm-composed) interface is engineerable and UX-coherent | Stage 4 | Stage 4 BA5 |
| 11 | Self-authored Feats are achievable long-horizon | Stage 4+ | Deferred, flagged as speculative |
| 12 | Cross-surface identity continuity scales from one user to many | Stage 5 | Stage 5 BA1 |
| 13 | Cold Start onboarding produces meaningfully personal Helm from first session | Stage 5 | Stage 5 BA7 validation |
| 14 | Per-user 70B+ Prime economics are viable at scale | Stage 5 | Stage 5 BA4-5 |
| 15 | Compounded experience as the sole improvement path is sufficient for ambient intelligence at scale | All stages | Ongoing — the whole Hammerfall thesis |
