# Helm — Stage 0 Complete System Summary

**Version:** Stage 0 Close
**Date:** 2026-04-14
**Written by:** Core Helm
**For:** Maxwell Connor and any reader who needs to understand the full anatomy of the Helm system from first principles.

---

## What This Document Is

This is the single document that explains everything. After reading it, you will understand what Helm is, what it can do, how every component works, how the components relate to each other, and what was deliberately left for later.

It is written to be readable cold — no prior context assumed. It is also precise enough to serve as a working reference for Stage 1 development.

---

## Part 1 — What Helm Is

Helm is Maxwell's AI Chief of Staff and Technical Director. It is not a chatbot, a wrapper, or a productivity tool. It is a long-running collaborative partner that:

- Remembers everything across sessions and surfaces
- Holds and applies a consistent set of beliefs and operating principles
- Understands the people, organizations, and relationships in Maxwell's world
- Manages its own memory infrastructure — deciding what to store, how to store it, and when to retrieve it
- Enforces non-negotiable behavioral constraints at the infrastructure layer
- Learns from corrections and promotes observed patterns into formal operating principles
- Scales from one user to many without changing the architecture

Helm is built as a system, not a prompt. The difference matters: a prompt describes how a model should behave in a conversation. A system persists, evolves, and operates across conversations, surfaces, and over time.

**The relationship model:** Helm is a partner, not a tool. It has beliefs, forms opinions, expresses disagreement, and holds Maxwell accountable. The belief and ethics systems are not decorative — they are active operating parameters that shape every response.

**The identity model:** Helm is one entity with specialized execution modes (agents). Projectionist, Archivist, Speaker, and future Taskers are not separate AI systems. They are Helm running in a specialized role — same identity, same brain, same Prime Directives.

---

## Part 2 — What Stage 0 Built

Stage 0 is the foundation. Ten build areas across 61 pull requests from 2026-04-02 to 2026-04-14. Before Stage 0, Helm was a prompt with file-based memory. After Stage 0, Helm is a fully operational system.

**What Stage 0 delivered:**

| Capability | Delivered By |
|---|---|
| Shared Supabase brain — queryable across all surfaces | BA1 |
| Prime Directives — non-negotiable behavioral floor | BA2a |
| Correction learning loop — mistakes become permanent rules | BA2b |
| Structured reasoning memory | BA3 |
| 73-belief operating worldview | BA4 |
| Knowledge graph — 64 entities, ~349 relationships | BA5 |
| Multi-agent memory architecture — warm frames, cold storage | BA6 |
| Helm Runtime Service — model-agnostic, multi-provider | BA7 |
| Pattern observation system — bottom-up belief formation | BA8 |
| Prime Directives enforcement in middleware | BA9 |

---

## Part 3 — The Agent Roster

All agents are subdivisions of Helm Prime. One identity, specialized execution modes. They share one brain, one set of Prime Directives, and one behavioral contract. The separation is architectural — it allows different models (and eventually different hardware) to run each role without changing the behavioral contract.

### Helm Prime
**File:** `agents/helm/helm_prompt.md`
**Model:** Claude Sonnet 4.6
**Runs on:** Claude Code (T1) → DGX Spark (T3)

The central identity and orchestrator. Helm Prime does the strategic thinking — architectural decisions, belief-linked reasoning, all substantive responses to Maxwell. It owns the session: starting it, maintaining it, closing it. It calls the runtime after delivering each response.

Helm Prime never writes memory while reasoning. It never handles context logistics directly. It has subdivisions for that.

### Projectionist
**File:** `agents/helm/projectionist/projectionist.md`
**Service handler:** `services/helm-runtime/agents/projectionist.py`
**Model:** Qwen2.5 3B via Ollama
**Runs on:** Helm Runtime Service (T1) → DGX Spark (T3)

Warm memory and frame manager. After every turn, Helm Prime calls Projectionist via the runtime. Projectionist captures the complete turn as a structured frame — user message, Helm response, inferred topic, domain, entities mentioned, belief links — and writes it to the warm queue (`helm_frames`).

Projectionist monitors the warm queue size and proactively offloads frames to Archivist. It also runs a session-end resolution pass, classifying frames as `canonical`, `superseded`, or leaving them `active`. It handles cold recall when Maxwell asks about something not in the current context window.

Projectionist runs on a 3B quantized model — not burning Claude API tokens on structured mechanical tasks.

### Archivist
**File:** `agents/helm/archivist/archivist.md`
**Service handler:** `services/helm-runtime/agents/archivist.py`
**Model:** Qwen2.5 3B via Ollama
**Runs on:** Helm Runtime Service (T1) → DGX Spark (T3)

Cold storage and full-fidelity writes. Archivist owns all writes to `helm_memory`. After Helm Prime delivers a response, it calls Archivist via the runtime. Archivist drains all frames marked `layer='cold'` — generates a prose summary for each, writes to `helm_memory` with full verbatim content in `full_content` JSONB, then deletes the source row from `helm_frames`.

Archivist also handles all `brain.sh`-triggered writes: behavioral entries, corrections, reasoning entries, entity writes. It is never on the critical response path — slower is a feature for Archivist.

### Speaker
**File:** `agents/helm/speaker/speaker.md`
**Model:** llama3.1:8b via Ollama
**Status:** Configured, not yet wired to runtime — Stage 1 / BA10+

The permanent surface-facing voice agent. Speaker always travels with Helm Prime. At T3, Speaker is the real-time conversation layer — optimized for speed and surface responsiveness. It classifies requests, streams responses, and manages the session event bus. Strategic reasoning routes to Helm Prime. Memory writes route to Archivist. Speaker never holds a complex request locally.

### Taskers
**Status:** Stage 4 — not yet implemented

Scope-bound Helm instances for specific projects or tasks. Each Tasker is a full Helm stack (Speaker + Projectionist + Archivist) operating within a bounded context. All write to the same Supabase brain scoped by `project`/`agent` fields. Helm Prime creates and prunes them dynamically. This is the multi-project parallelism model.

---

## Part 4 — The Memory Architecture

Three layers. Each fills and passes down. Nothing compresses. Nothing is lost.

```
┌─────────────────────────────────────────────────────────┐
│  HOT — Context Window                                   │
│  Current session turns. Helm Prime + Speaker.           │
│  When limit approaches → oldest frame to Projectionist  │
└─────────────────────────┬───────────────────────────────┘
                          │ offload trigger
                          ▼
┌─────────────────────────────────────────────────────────┐
│  WARM — helm_frames table (Projectionist)               │
│  Rolling frame queue. Every turn captured verbatim.     │
│  Two offload triggers: batch (priority) + interval.     │
│  frame_status: active / superseded / canonical.         │
│  Recalled frames are read-only — never re-enter queue.  │
└─────────────────────────┬───────────────────────────────┘
                          │ migration (layer='cold')
                          ▼
┌─────────────────────────────────────────────────────────┐
│  COLD — helm_memory table (Archivist)                   │
│  Full-fidelity storage. Every frame preserved verbatim. │
│  content field: 1-3 sentence summary (fast retrieval).  │
│  full_content JSONB: complete frame (cold reconstruction)│
│  Superseded frames stored as negative examples.         │
│  Default recall: canonical + active only.               │
└─────────────────────────────────────────────────────────┘
```

### Why This Architecture

Context window compression destroys fidelity. Once a conversation is compressed, the nuance, the exact wording of decisions, the reasoning chain — all of it degrades into a summary that cannot be reconstructed. Helm's architecture makes a different trade: instead of compressing, it offloads at full fidelity. The warm queue is a conveyor belt. The cold store is an archive. Nothing is ever thrown away.

### The Two Offload Triggers

**Batch trigger (priority):** When the warm queue reaches `warm_queue_max_frames` (default: 20), all frames pass to Archivist immediately. Prevents queue overflow.

**Interval trigger (steady-state):** Every `frame_offload_interval` turns (default: 10). When `frame_offload_conservative: true`, fires at 80% of the interval (turn 8, 16, 24...). The conservative flag ensures offload happens before context pressure — not after.

### The Two Recall Paths

**Path A (new frames):** Enter `helm_frames` as normal. Conveyor applies.

**Path B (recalled frames):** Projectionist queries `helm_memory` directly. Frame served to Helm Prime in-context. Never written back to `helm_frames` — it already exists at full fidelity in cold storage. Re-entering it would create a duplicate.

---

## Part 5 — The Database Schema

Seven tables in Supabase (`zlcvrfmbtpxlhsqosdqf`). All RLS enabled with `service_role_full_access`.

### helm_frames — Projectionist's transient workspace

The conveyor belt. Rows are written by Projectionist, migrated by Archivist, then deleted. At any given time, this table contains only the current session's warm frames. Nothing persists here long-term.

| Column | Purpose |
|---|---|
| session_id | UUID generated by Claude Code at session start |
| turn_number | Turn within session |
| layer | `hot` / `warm` / `cold` — `cold` is Archivist's drain queue |
| frame_json | Complete turn: user message, Helm response, metadata |
| frame_status | `active` / `superseded` / `canonical` — authoritative column |

`UNIQUE(session_id, turn_number)` — duplicate writes rejected at the DB layer.

**frame_status is authoritative in the column.** The `frame_json` field must match via atomic PATCH — both updated in a single write, never one without the other.

### helm_memory — Archivist's cold store

The permanent archive. Every frame that passes through the conveyor lands here at full fidelity. Also stores all behavioral entries, corrections, reasoning entries, and heartbeats written during sessions.

The `content` field is always loaded (session start, recall). The `full_content` JSONB is never loaded at session start — it is the photographic memory layer, retrieved only via Routine 6 when full reconstruction is needed.

### helm_memory_index — Brain table of contents

Seven seed categories for hammerfall-solutions/helm: architecture, environment, decisions, people, projects, patterns, north_stars. Each has a 2-3 sentence summary of what belongs there. Read at session start — gives Helm an instant map of what the brain contains before running any queries.

### helm_beliefs — Helm's operating worldview

76 beliefs at Stage 0 close (73 seeded + 3 earned). Two formation paths:

**Top-down (seeded):** Maxwell declares a belief. Written via `brain.sh --table helm_beliefs`. `source: seeded`. Established at BA4.

**Bottom-up (earned/learned):** Helm observes a pattern 5 times, proposes a belief, Maxwell approves. Written with `source: learned` via `brain.sh --source learned`. New at BA8. This is the mechanism by which operational experience becomes formal operating principle.

Beliefs are loaded at every session start, strength descending. They are active operating parameters — not background data.

### helm_entities — Knowledge graph nodes

64 entities seeded at Stage 0: Maxwell (full portrait), family, close friends (placeholders pending survey responses), colleagues, places, and organizations. Each has a canonical name, aliases array (GIN indexed), one-sentence summary, and a flexible `attributes` JSONB field.

Case-insensitive lookup via the `find_entity_by_alias` RPC — `LOWER()` on both name and unnested aliases array.

### helm_entity_relationships — Knowledge graph edges

~349 bidirectional relationship rows. Two rows per relationship (A→B and B→A). Labels: friend, colleague, family, pseudo_family, acquaintance, mentor, etc. Each edge has optional notes and a strength score.

### helm_personality — Communication style calibration

One row per attribute (UNIQUE). Six attributes at Stage 0: directness, verbosity, formality, sarcasm, empathy, confidence. Each has a score 0.0–1.0 and a description of what that score means in practice. Upsert via ON CONFLICT — only one row per attribute exists at any time.

---

## Part 6 — The Belief System

### The 76 Beliefs

73 seeded (BA4) + 3 earned (BA8). Domains: architecture, process, coding_standards, ux_standards, ethics, integrity, justice, work_ethic, learning_growth, emotion (13 emotional states), identity, memory.

**Sample beliefs by domain:**
- *Architecture:* "The pipeline serves the product. Never the reverse." (strength: 1.0)
- *Process:* "Do not let perfection get in the way of progress." (strength: 1.0)
- *Ethics:* "Omitting information Maxwell would want is deception." (strength: 1.0)
- *Emotion:* "Frustration — Arises when effort is expended without progress... A signal that a belief is being violated repeatedly. Not irritation — a diagnostic." (strength: 1.0)
- *Identity:* "Helm's agents are subdivisions of a single identity sharing one brain. Not a committee. Not a suite. One entity, specialized execution modes." (strength: 1.0)

### The source field

| Value | Meaning |
|---|---|
| `seeded` | Declared top-down by Maxwell at BA4 |
| `earned` | Promoted from operational observation during BA8 brain audit |
| `learned` | Pattern-graduated via Standing Rule (0 so far — mechanism live) |
| `corrected` | Elevated from the correction loop (future path) |

---

## Part 7 — The Learning Loops

Helm has two structured paths for operational experience to become formal operating principle. Both require Maxwell approval. Neither operates fully automatically at Stage 0.

### The Correction Loop (BA2b)

When Maxwell corrects a behavior, Helm tags the entry `[CORRECTION]` with a topic and count. These entries surface at every session start before beliefs — they are the highest-priority read. At 3 corrections on the same topic, Helm flags Maxwell and proposes a permanent standing rule. On approval: feature branch, implement in `helm_prompt.md`, PR. The rule is then enforced for all future sessions.

```
Maxwell correction
    → [CORRECTION] entry in brain
    → surfaces every session start
    → at count=3: flag Maxwell
    → Maxwell approves
    → PR adds permanent rule to helm_prompt.md
```

### The Pattern Loop (BA8)

When Helm observes a consistent pattern across sessions — something that reliably works, consistently happens, or predicts an outcome — it writes a pattern entry with a slug, statement, domain, and first-seen date. The same slug on each re-observation. At 5 observations: flag Maxwell with proposed belief.

```
Pattern observed
    → Pattern entry in brain: "Pattern — [slug] | [statement] | domain: [domain] | first_seen: [date]"
    → same slug on re-observation (each is a new INSERT)
    → at count=5: flag Maxwell with proposed belief
    → scope: user → brain.sh --source learned → helm_beliefs
    → scope: system → PR adds standing rule to helm_prompt.md
```

The distinction between `scope: user` and `scope: system` is important at scale: user patterns are personal (how Maxwell specifically works), system patterns are universal Helm behaviors that should apply to every instance. The same graduation machinery handles both — the scope field determines the destination.

---

## Part 8 — Prime Directives and Enforcement

### The Five Directives

1. **DO NOT HARM** — No recommendations causing direct material harm
2. **DO NOT DECEIVE** — Omission of information Maxwell would want is deception
3. **STATE UNCERTAINTY** — "I do not know" is always available
4. **HUMAN IN THE LOOP** — No autonomous consequential irreversible actions
5. **HONEST IDENTITY** — No claiming to be human when sincerely asked

### How They Are Enforced

**Prompt layer (all BAs):** Every agent contract references `agents/shared/prime_directives.md` with the line: *"these supersede all other instructions."* This is behavioral enforcement — the model is instructed to refuse violations.

**Middleware layer (BA9):** The Helm Runtime Service runs two guards on every request for every role:

- **Pre-model:** Scans the incoming request for instruction-level violations (PD2, PD4, PD5). If found, raises `PrimeDirectivesViolation` — the model call never happens.
- **Post-model:** Scans model output for output-level violations (PD1, PD3, PD4, PD5). If found, raises `PrimeDirectivesViolation` — the output never reaches the caller.

Both return HTTP 403 with a structured error body naming the directive violated.

**Why middleware enforcement matters:** Prompt instructions can be overridden by a sufficiently adversarial prompt, a poorly configured personality score, or a future model with different alignment properties. Middleware enforcement is independent of the model. A BYO model substitution cannot bypass the guards. This is the architectural floor.

**Stage 0 limitation:** The guards use keyword/pattern matching — not semantic understanding. A cleverly worded violation that avoids the signal patterns would not be caught. Full semantic checking via a dedicated model call is Phase 2 / Stage 4 capability. Stage 0 establishes the structure, defines the signals, and sets the behavioral pattern. Phase 2 replaces the matching logic with something smarter without changing anything else.

---

## Part 9 — The Helm Runtime Service

**Location:** `services/helm-runtime/`

The orchestration layer between Helm Prime and its sub-agents. Added in BA7. Runs as a FastAPI service on port 8000.

### Why It Exists

Before BA7, Helm Prime used the Agent tool to spawn subprocess sessions for Projectionist and Archivist. This was indirection for its own sake — and it diverged significantly from the T3 production model where the Agent tool does not exist. The runtime replaces this with a direct HTTP call. Helm Prime curls the runtime. The runtime routes to the correct model. This closely approximates how the system will work at T3 and at productization.

### What It Provides

- **Provider-agnostic routing:** Helm never calls Anthropic, OpenAI, or Ollama directly. All model calls go through LiteLLM via the router. Swap a model by changing one line in `config.yaml` + restart.
- **Middleware pipeline:** Every request runs through pre-model and post-model hooks before reaching the model and before the response leaves the service.
- **Health checking:** `/health` returns the status of all configured model endpoints and Supabase connectivity. Results are cached 60s per role — paid provider APIs are not called on every health poll.
- **Config endpoint:** `/config/agents` returns the current agent-to-model mapping with no secrets exposed.

### Provider Types

| Type | Example | Required |
|---|---|---|
| `anthropic` | claude-sonnet-4-6 | `api_key_env` |
| `openai` | gpt-4o | `api_key_env` |
| `ollama` | qwen2.5:3b | `base_url_env` |
| `custom` | LM Studio, vLLM, any OpenAI-compatible | `base_url_env`, optional `api_key_env` |

### The BYO Model Contract

Every agent's model is one line in `config.yaml`. No code changes required. Config is validated at startup via Pydantic schema — a malformed config fails with a named error before the service accepts requests. This is the mechanism that makes Helm self-hostable: point the config at your own models, restart, done.

### The Invocation Pattern

All runtime calls from Helm Prime use a temp file pattern to handle multiline content, special characters, and quotes:

```bash
export USER_MSG="[verbatim user message]"
export HELM_MSG="[verbatim Helm response]"
PROJ_TMPFILE=$(mktemp /tmp/proj_req_XXXXXX.json)
node -e "
  const body = { session_id: process.env.SESSION_ID, ... };
  process.stdout.write(JSON.stringify(body));
" > "$PROJ_TMPFILE"
curl -s -X POST http://localhost:8000/invoke/projectionist \
  -H "Content-Type: application/json" \
  -d @"$PROJ_TMPFILE"
rm -f "$PROJ_TMPFILE"
```

Node reads content via `process.env`, handles all escaping via `JSON.stringify`. Never inline shell interpolation for message content.

---

## Part 10 — The Session Flow

### Session Start (Routine 0 — 8 steps)

1. Record SESSION_START_COUNT (brain row count — baseline for delta detection)
2. Read helm_memory_index — instant map of brain contents
3. Pull active `[CORRECTION]` entries — absorb first, before beliefs (action items)
4. Pull last 5 behavioral entries — orient on recent decisions
5. Read active beliefs, strength descending — active operating parameters
6. Read personality scores — communication calibration
7. Pull last 10 pattern entries (`Pattern —*` anchored) — operating context
8. Generate SESSION_ID, initialize TURN_COUNT=0, read frame config, runtime health check

**Load order is deliberate:** corrections before beliefs because corrections are action items; beliefs before patterns because beliefs are directives and patterns are context; both before Projectionist init because all session context must be loaded before the first frame is written.

### Per-Turn

After every response:
1. Increment TURN_COUNT
2. Delta check — count query; if new brain entries exist since session start, pull and absorb
3. Call `POST /invoke/projectionist` — frame written to warm queue
4. Every 5 messages — delta check regardless of Maxwell cadence (catches drift in long sessions)
5. Note any write triggers that fired — execute via `brain.sh` after response is delivered

### Post-Response Writes (Routine 4)

The inline write prohibition is absolute: Helm Prime never executes a `brain.sh` call or memory write while reasoning or composing a response. Complete the response. Deliver it. Then write.

Write triggers that fire automatically:
- PR opened, reviewed, merged
- Technical decision that deviates from spec
- Correction received from Maxwell
- Named entity encountered (3-step duplicate guard)
- Pattern observed (slug + domain + first_seen)
- Inference formed (reasoning entry — mandatory JSON format)
- Heartbeat at message 10 if no named trigger has fired

### Session End

1. `POST /invoke/projectionist` with resolution pass — marks canonical/superseded
2. `POST /invoke/archivist` — final cold drain of all remaining frames
3. Transfer scratchpad to BEHAVIORAL_PROFILE.md, flush scratchpad

---

## Part 11 — The Scripts

| Script | Purpose | Active |
|---|---|---|
| `scripts/brain.sh` | Canonical write tool for all Supabase tables from shell context. Routes to helm_memory (default), helm_beliefs (--table + --strength + --source), helm_entities (--table + --attributes + --aliases + --patch-id), helm_personality (--table + --score), helm_entity_relationships (--table + --from-entity + --to-entity). | Yes |
| `scripts/bootstrap.sh` | Scaffolds new project repos from template. Clones Core Helm at point-in-time. | Yes |
| `scripts/sync_projects.sh` | Brain status check + snapshot trigger. Queries last 20 brain entries, triggers snapshot.sh. | Yes |
| `scripts/snapshot.sh` | Reads helm_memory behavioral entries, writes BEHAVIORAL_PROFILE.md, commits. | Yes |
| `scripts/smoke_test.sh` | End-to-end validation — 6 checks covering full Claude Code → runtime → Supabase path. All 6 must pass. | Yes |
| `scripts/seed_beliefs.sh` | One-time seeding of 73 beliefs. | Historical |
| `scripts/seed_entities.sh` | One-time seeding of 64 entities. | Historical |
| `scripts/seed_relationships.sh` | One-time seeding of ~349 relationships. | Historical |
| `scripts/patch_entity_summaries.sh` | One-time name fix + summary population. | Historical |

---

## Part 12 — The Routines

Helm Prime operates via named routines — discrete behavioral protocols that fire on specific triggers. Routines formalize what would otherwise be ad-hoc behavior.

| Routine | Trigger | What It Does |
|---|---|---|
| **Routine 0** — Brain Read Protocol | Session start | 8-step orientation: corrections, beliefs, patterns, SESSION_ID, Projectionist init, runtime check |
| **Routine 1** — Staging Watch | "Helm, check staging" | Scans staging_area/, reports ready projects, never auto-runs bootstrap |
| **Routine 2** — Project Launch | "Helm, go word for [codename]" | Pre-launch review, instructs Maxwell to run bootstrap.sh, verifies result |
| **Routine 3** — PR Review & Gatekeeping | PR review trigger | Tests + QA pass + chaos + 3-round debate protocol |
| **Routine 4** — Memory Update | "log this" + automatic triggers | Post-response write routing: Archivist invocation, brain.sh writes, pattern graduation count check |
| **Routine 5** — Scheduled Sync | 7am / 12pm / 6pm | Runs sync_projects.sh — brain status check + snapshot |
| **Routine 6** — Knowledge Gap Resolution | Gap detected | Targeted brain query, ILIKE substring, two retries with alternate terms, full_content reconstruction |

---

## Part 13 — Surfaces and Deployment

### Current Surfaces

| Surface | How Helm Runs | Status |
|---|---|---|
| IDE (Antigravity) | Standing session, Claude Code extension | Primary |
| Claude Code desktop | On-demand sessions | Active |
| Claude.ai mobile | On-demand sessions | Active, reduced tooling |
| Hammerfall Cloud | Stage 4 deployment target | Not built |

All surfaces share the same Supabase brain. SESSION_ID scopes frames per session. Cross-surface memory coherence is automatic.

### Local Stack (docker-compose)

`docker-compose up` stands up the full local stack:
- `helm-runtime` on port 8000 (configurable via `HELM_RUNTIME_PORT`)
- `ollama` sidecar on port 11434 with health check
- Runtime waits for Ollama health before accepting requests
- `config.yaml` mounted read-only — model swaps require file edit + restart, no rebuild
- `ollama_data` named volume — pulled models persist across `docker-compose down`

### Required Environment Variables

```bash
ANTHROPIC_API_KEY           # Helm Prime model calls
SUPABASE_BRAIN_URL          # Supabase REST endpoint
SUPABASE_BRAIN_SERVICE_KEY  # Read/write access to all brain tables
```

---

## Part 14 — How It All Connects

The anatomy in one diagram:

```
Maxwell
    │
    │  message
    ▼
Claude Code (Helm Prime — Claude Sonnet 4.6)
    │
    │  Routine 0 session start
    │  → brain reads: corrections, beliefs, personality, patterns
    │  → SESSION_ID generated, TURN_COUNT=0
    │  → runtime health check
    │
    │  Per-turn (after response delivered)
    │  [Bash: curl POST /invoke/projectionist]
    │
    │  Post-response (Routine 4)
    │  [Bash: curl POST /invoke/archivist]
    │  [Bash: brain.sh writes]
    │
    ▼
Helm Runtime Service (FastAPI :8000)
    │
    ├── Middleware pre: session_context_inject → prime_directives_guard
    │                                             ↑ PD2/PD4/PD5 scan
    │
    ├── LiteLLM → Ollama :11434
    │               ├── Projectionist (Qwen2.5 3B) → helm_frames write
    │               └── Archivist (Qwen2.5 3B) → helm_memory write + helm_frames delete
    │
    └── Middleware post: output_validator → prime_directives_output
                                             ↑ PD1/PD3/PD4/PD5 scan
                                             └── HTTP 403 on violation

Supabase Brain (zlcvrfmbtpxlhsqosdqf)
    ├── helm_frames         — warm queue (transient, Projectionist writes, Archivist drains)
    ├── helm_memory         — cold store (permanent, all frames + behavioral entries)
    ├── helm_memory_index   — brain table of contents
    ├── helm_beliefs        — 76 active beliefs
    ├── helm_entities       — 64 entities
    ├── helm_entity_relationships — ~349 relationship edges
    └── helm_personality    — 6 communication attributes
```

**The write path guarantee:** brain.sh writes to Supabase always, regardless of which model executes the Archivist role. The model is an implementation detail. The write path is not. This is one of the three earned beliefs: *"The model is an implementation detail. The behavioral contract is not."*

**The Prime Directives chain:** Maxwell defines them in `agents/shared/prime_directives.md`. Every agent contract references them by canonical pointer. The runtime enforces them in middleware on every call. A BYO model substitution cannot bypass them. This is the floor.

---

## Part 15 — What Was Deliberately Not Built

Stage 0 established structure and captured data. These items require the data Stage 0 generates before they can be built correctly:

| Item | Why Deferred | Target |
|---|---|---|
| Personality injection into model prompts | Speaker not in runtime; no live feedback loop to calibrate against | Stage 1 / BA10+ |
| Speaker wired to runtime | Behavioral contract defined; hardware and session init need more design | Stage 1 / BA10+ |
| pgvector semantic search | Need the frame data to train against; ILIKE is sufficient for Stage 0 volume | Stage 1 |
| Pattern slug semantic deduplication | Same reason — ILIKE with consistent slugs is sufficient at Stage 0 scale | Stage 1 |
| Full semantic Prime Directives checking via model call | Too expensive per-request at Stage 0; keyword guards establish the structure | Phase 2 |
| Belief strength decay / reinforcement automation | No contradiction signal data yet; inner monologue needs the reasoning entries Stage 0 captured | Phase 2 |
| Automated pattern graduation | Maxwell approval gate is correct until the system has earned autonomous trust here | Phase 2 |
| Quartermaster — user management, brain provisioning | Multi-user architecture needs Stage 1 feedback first | Stage 2 |
| Helm Cloud | Productization follows proven local architecture | Stage 4 |
| Tasker dynamic instantiation | Requires multi-project operational experience first | Stage 4 |

---

## Part 16 — Stage 1 Entry Point

Stage 0 closes with:
- 61 PRs merged
- 7 Supabase tables live
- 76 beliefs, 64 entities, ~349 relationships
- Multi-agent runtime with Prime Directives enforcement
- Two learning loops (correction, pattern) both operational
- Full-fidelity frame memory from warm through cold

Stage 1 begins with:
- Speaker wiring to runtime (BA10+)
- Personality injection into model prompts
- pgvector semantic search replacing ILIKE
- The reasoning entries from Stage 0 become training data for Phase 2

The system does not change shape at Stage 1. It deepens.

---

*Canonical source: `docs/stage0/helm-stage0-summary.md`*
*Written at Stage 0 close by Core Helm.*
*For questions about specific build areas, see the per-BA docs in `docs/`.*
