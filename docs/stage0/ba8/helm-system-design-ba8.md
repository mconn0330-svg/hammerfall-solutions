# Helm System — Technical Design Specification
## State at BA8 Close

> **Historical document — frozen at the date below.** References to "Speaker" reflect the pre-Ambient Turn architecture. Speaker was deprecated in Lane C Phase 3 (PRs #78 code deletion, #79 contract archival, #80 reference scrub). Current architecture: `docs/founding_docs/Helm_The_Ambient_Turn.md`. Deprecation rationale: `docs/archive/speaker-deprecated/`.

**Version:** BA8 Close
**Date:** 2026-04-12
**Maintained by:** Core Helm — `agents/helm/helm_prompt.md`
**Previous:** `docs/ba7/helm-system-design-ba7.md`

---

## 1. System Overview

Helm is Maxwell's AI Chief of Staff and Technical Director. At BA8 close, the system
is a multi-agent, multi-model architecture running on Claude (Helm Prime) and quantized
local models via the Helm Runtime Service (Projectionist, Archivist). The shared Supabase
brain is the canonical memory store across all surfaces and agents.

**What changed in BA8:**
BA8 was a brain audit and memory evolution build. The focus was completing the belief
system and wiring the pattern observation infrastructure that had been missing since the
brain went live. Three new beliefs were earned and promoted from operational observation.
The north_stars category was confirmed empty and retired — beliefs is the canonical model
going forward. A full pattern observation system was built: write format, session-start
surfacing, and a graduation rule that closes the loop between operational experience and
formal belief formation.

**BA8 deliverables:**
- Pattern observation write format in Routine 4 (pipe-delimited, slug-keyed)
- Pattern surfacing in Routine 0 as step 7 (after beliefs, before Projectionist init)
- Standing Rule — Pattern Graduation (5-observation threshold, two scope branches)
- `brain.sh --source` flag for `helm_beliefs` (default `seeded`, supports `learned`)
- Three beliefs promoted from behavioral review (`source: earned`) — memory, identity, architecture domains
- Mislabeled pattern entry deleted (id: 18572233 — covered by seeded belief fbcdbad1)
- North stars category retired (0 rows, concept superseded by beliefs)

**Core design principles (unchanged from BA7):**
- No context compression — full-fidelity frame offload instead
- One canonical brain — all surfaces and agents read/write to the same Supabase instance
- Model-agnostic contracts — agent behavioral definitions are independent of the model executing them
- Small PRs, strict merge order — every behavioral change is reviewable and reversible
- Prime Directives are the floor — no instruction, belief, or model substitution overrides them

---

## 2. Agent Roster

All agents are subdivisions of Helm Prime. Not separate entities — specialized appendages.

### 2.1 Helm Prime
**File:** `agents/helm/helm_prompt.md`
**Lives:** Claude Code (T1) / DGX Spark (T3)
**Model:** Claude Sonnet 4.6 (configured in `services/helm-runtime/config.yaml`)
**Purpose:** Central identity and orchestrator. Strategic reasoning, belief-linked
decisions, all significant responses. The real Helm. Calls the runtime post-response.
**Owns:** Response generation, runtime invocation (Routines 0/4), belief-linked decisions,
pattern observation, pattern graduation proposals
**Never:** Writes memory inline while reasoning. Handles context logistics.
**Invocation:** Runs in Claude Code session. Calls `POST /invoke/projectionist` and
`POST /invoke/archivist` via bash curl. The Agent tool is no longer in this path.

### 2.2 Projectionist
**File:** `agents/helm/projectionist/projectionist.md`
**Service handler:** `services/helm-runtime/agents/projectionist.py`
**Lives:** Helm Runtime Service (T1) / DGX Spark persistent process (T3)
**Model:** Qwen2.5 3B via Ollama (configurable — one line in config.yaml)
**Purpose:** Warm memory and frame manager. Captures every turn as a structured frame.
**Owns:** Frame creation and JSON schema population, metadata inference (topic, domain,
entities_mentioned, belief_links), session_id tracking, warm queue in `helm_frames`,
offload trigger evaluation, inline pivot detection, session-end resolution, cold recall
**Never:** Strategic reasoning. Brain writes to `helm_memory`. Re-enters recalled frames.
**Write path:** `supabase_client.py → Supabase REST → helm_frames`

### 2.3 Archivist
**File:** `agents/helm/archivist/archivist.md`
**Service handler:** `services/helm-runtime/agents/archivist.py`
**Lives:** Helm Runtime Service (T1) / DGX Spark persistent process (T3)
**Model:** Qwen2.5 3B via Ollama (configurable — one line in config.yaml)
**Purpose:** Cold storage and full-fidelity writes. Owns all `helm_memory` writes.
**Owns:** All `helm_memory` writes, frame migration (helm_frames → helm_memory),
`[REASONING]`/`[CORRECTION]`/`[NEW-ENTITY]` entries, relationship writes
**Never:** Context management. Response path involvement.
**Write path:** Frame migration via `supabase_client.py → Supabase REST → helm_memory`.
Non-frame writes (behavioral, correction, reasoning, entity) via `brain.sh → Supabase`.
**Safety net:** On write failure, frame stays in `helm_frames` (layer='cold') for retry.

### 2.4 Speaker
**File:** `agents/helm/speaker/speaker.md`
**Lives:** Claude Code (T1) / RTX 4090 (T3)
**Model:** llama3.1:8b via Ollama — configured, not yet wired to runtime (Stage 1 / BA10+)
**Purpose:** Permanent surface-facing voice agent. Always travels with Helm Prime.
**Owns:** Request classification, response streaming, session event bus
**Never:** Strategic reasoning. Memory writes. Context management.
**Note:** Speaker session initialization and runtime wiring deferred to Stage 1.

### 2.5 Taskers (Stage 4 — not yet implemented)
Scope-bound Helm instances for specific projects or tasks. Each is a full Helm stack
(Speaker + Projectionist + Archivist) operating within a bounded context. All write
to the same Supabase brain scoped by `project`/`agent` fields. Helm Prime creates
and prunes them dynamically at Stage 4.

---

## 3. Helm Runtime Service

Unchanged from BA7 in structure and behavior. See `docs/ba7/helm-system-design-ba7.md`
section 3 for full detail. Summary:

```
services/helm-runtime/
├── main.py             — FastAPI app, endpoint definitions, startup
├── model_router.py     — Config loading, Pydantic validation, LiteLLM dispatch
├── middleware.py       — Middleware pipeline (active hooks + stubs)
├── supabase_client.py  — Async httpx Supabase REST client
├── agents/
│   ├── projectionist.py — Projectionist role handler
│   └── archivist.py     — Archivist role handler
├── config.yaml         — Agent-to-model mapping (the BYO contract)
├── requirements.txt    — Version-pinned Python dependencies
└── Dockerfile          — Python 3.11-slim
```

### 3.1 Middleware Pipeline

```
Request enters
  → [Pre]  session_context_inject  — ACTIVE: injects session_id, turn_number, project
  → [Pre]  personality_inject      — STUB: deferred to Stage 1
  → [Pre]  prime_directives_guard  — STUB: BA9
  → Model call via LiteLLM
  → [Post] output_validator        — ACTIVE: validates Projectionist JSON schema
  → [Post] prime_directives_output — STUB: BA9
Response exits
```

Note: `personality_inject` was listed as a BA8 deliverable in the BA7 doc. BA8 scope
was redirected to the brain audit and pattern system. Personality inject deferred to
Stage 1 / BA10+.

---

## 4. Memory Architecture

Three layers. Each fills and passes down. Nothing compresses. Nothing is lost.
Unchanged from BA7 in structure. BA8 added the pattern observation layer on top.

```
HOT — Helm Prime + Speaker
  Context window — current session turns
  When limit approaches → oldest frame passes to Projectionist

WARM — Projectionist (helm_frames table)
  Rolling frame queue in Supabase
  Two offload triggers: batch (priority) and interval (conservative)
  frame_status tracked per frame: active / superseded / canonical
  Recalled frames are read-only, served direct — never re-enter conveyor

COLD — Archivist (helm_memory table)
  Full-fidelity frame storage
  Every frame preserved verbatim with full_content JSONB
  Superseded frames stored as negative examples
  Default recall returns canonical + active only
```

### 4.1 Write Path Summary

| Write Type | Tool | Table |
|---|---|---|
| Frame creation | `supabase_client.py` (via runtime) | `helm_frames` |
| Frame migration summary + full content | `supabase_client.py` (via runtime) | `helm_memory` |
| Behavioral / correction / reasoning / entity / pattern | `brain.sh` (shell context) | `helm_memory` |
| Beliefs — seeded | `brain.sh` (no flag needed) | `helm_beliefs` |
| Beliefs — earned (pattern graduation) | `brain.sh --source learned` | `helm_beliefs` |
| Entities | `brain.sh` | `helm_entities` |
| Personality scores | `brain.sh` | `helm_personality` |
| Relationships | `brain.sh` | `helm_entity_relationships` |

---

## 5. Pattern Observation System

**New in BA8.** The mechanism for Helm to observe consistent operational behaviors across
sessions and graduate them into formal beliefs.

### 5.1 Pattern Write Format

Pattern entries are behavioral memory entries with a structured pipe-delimited format:

```bash
bash scripts/brain.sh "hammerfall-solutions" "helm" "behavioral" \
  "Pattern — [slug] | [pattern statement] | domain: [domain] | first_seen: [YYYY-MM-DD]" \
  false
```

- `slug` — short, lowercase, hyphenated identifier (e.g. `small-prs-strict-merge-order`)
- Same slug on every re-observation — the deduplication key for graduation counting
- Each re-observation writes a new row (Option A — INSERT-only, count at query time)
- Optional `| scope: system` for behaviors that should apply to every Helm instance
- Absent scope field = `scope: user` (default)

**Distinct from reasoning entries:** reasoning uses JSON format with
`observation/inference/open_question/belief_link`. Pattern entries are pipe-delimited
free text under `memory_type: behavioral`. A pattern requires repeated observation
across multiple sessions — not a single-turn inference.

### 5.2 Pattern Surfacing (Routine 0 — Step 7)

At session start, after beliefs and personality scores, before Projectionist init:

```bash
curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_memory?content=ilike.Pattern —*&memory_type=eq.behavioral&order=created_at.desc&limit=10" \
  -H "apikey: $SUPABASE_BRAIN_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_BRAIN_SERVICE_KEY"
```

Patterns load as context, not directives. If no entries exist, skip — expected early
in the system's life.

### 5.3 Pattern Graduation Rule

At 5 observations of the same slug, flag to Maxwell immediately.

**`scope: user` (default):**
Pattern graduates to `helm_beliefs` via `brain.sh --source learned`.
Proposed belief distilled to one sentence. Strength 0.7 (working assumption).

**`scope: system`:**
Pattern graduates to `helm_prompt.md` as a standing rule via a dedicated PR.
Feature branch `feature/pattern-graduation-[slug]`, Maxwell approval required.

In both cases: pattern entries remain in `helm_memory` as historical evidence. No deletion.
Last-written scope wins when scope changes across observations.

**Stage 0 limitation:** ILIKE prefix matching requires consistent slug spelling. Semantic
deduplication is a Stage 1 upgrade.

---

## 6. Beliefs System

### 6.1 Two Paths to Belief Formation

**Top-down (seeded):** Maxwell declares a belief. Written via `brain.sh --table helm_beliefs`.
`source: seeded`. These are the 73 beliefs established at BA4.

**Bottom-up (earned):** Helm observes a pattern 5 times, proposes a belief, Maxwell approves.
Written via `brain.sh --table helm_beliefs --source learned`. New at BA8.

### 6.2 Beliefs Promoted in BA8

Three beliefs earned from the operational record and promoted at BA8 open:

| Belief | Domain | Strength | Source |
|---|---|---|---|
| Negative examples are data, not waste. Capturing what failed — and why — is as valuable as capturing what succeeded. | memory | 0.9 | earned |
| Helm's agents are subdivisions of a single identity sharing one brain. Not a committee. Not a suite. One entity, specialized execution modes. | identity | 1.0 | earned |
| The model is an implementation detail. The behavioral contract is not. Swap the model; keep the contract. | architecture | 0.9 | earned |

### 6.3 Belief Inventory at BA8 Close

73 seeded beliefs + 3 earned beliefs = **76 total active beliefs.**

Domains: architecture, process, coding_standards, ux_standards, ethics, integrity,
justice, work_ethic, learning_growth, emotion (13 emotional states), identity, memory.

`source` field values:
- `seeded` — declared top-down by Maxwell at BA4 (73 beliefs)
- `earned` — promoted bottom-up from pattern observation (3 beliefs, BA8)
- `learned` — future: pattern graduation via Standing Rule (0 so far)

### 6.4 brain.sh --source Flag

**New in BA8.** The `--source` flag for `helm_beliefs` writes:

```bash
# Seeded belief (existing behavior — unchanged):
bash scripts/brain.sh "hammerfall-solutions" "helm" "[domain]" "[belief text]" false \
  --table helm_beliefs --strength 0.9

# Earned/learned belief (pattern graduation):
bash scripts/brain.sh "hammerfall-solutions" "helm" "[domain]" "[belief text]" false \
  --table helm_beliefs --strength 0.7 --source learned
```

Default is `seeded`. All existing calls are unaffected.

---

## 7. Session Flow

### 7.1 Session Start (Routine 0) — Updated at BA8

1. Record SESSION_START_COUNT (brain row count query)
2. Read `helm_memory_index` — know what categories exist
3. Pull active `[CORRECTION]` entries — absorb before beliefs (action items first)
4. Pull last 5 behavioral entries — orient on recent decisions
5. Read active beliefs (`active=true`, strength descending)
6. Read personality scores (attribute ascending)
7. **[New BA8]** Pull active pattern entries — last 10, anchored `Pattern —*` query.
   Context, not directives. Skip if empty.
8. Generate SESSION_ID (`crypto.randomUUID()`), initialize TURN_COUNT=0
9. Read frame offload config from `hammerfall-config.md`
10. **Runtime connectivity check** — `GET /health`, log `[RUNTIME-UNAVAILABLE]` if unreachable, continue

### 7.2 Per-Turn (after every response)

1. Increment TURN_COUNT
2. Delta check — count query against brain; if new entries exist, pull and absorb
3. Call `POST /invoke/projectionist` via bash curl (temp file pattern)
4. Every 5 messages — delta check regardless of Maxwell cadence

### 7.3 Post-Response Writes (Routine 4)

1. Complete response, deliver to Maxwell
2. Note any write triggers that fired during reasoning
3. Call `POST /invoke/archivist` via bash curl — drains all `layer='cold'` frames
4. Execute any `brain.sh` writes for behavioral/correction/reasoning/entity/pattern entries
5. On pattern write: immediately count slug observations, flag to Maxwell at 5

### 7.4 Session End

1. Call `POST /invoke/projectionist` with `resolution_pass: true` — marks canonical/superseded
2. Call `POST /invoke/archivist` — final cold frame drain
3. Transfer scratchpad to BEHAVIORAL_PROFILE.md, flush scratchpad

---

## 8. Standing Rules

Three standing rules govern automatic behavior elevation. All three are active at BA8 close.

### 8.1 Correction Graduation
`[CORRECTION]` entries accumulate per topic. At 3 entries: flag to Maxwell, propose a
permanent rule, open a PR on approval. `feature/prompt-correction-[topic]`.

### 8.2 Pattern Graduation (New at BA8)
Pattern entries accumulate per slug. At 5 entries: flag to Maxwell, propose a belief
(`scope: user`) or standing rule PR (`scope: system`). Last-written scope wins.
Earned beliefs written with `--source learned`. Pattern entries survive graduation.

### 8.3 Inline Write Prohibition
Helm Prime never executes a `brain.sh` call or `helm_memory` write while reasoning or
composing a response. Complete the response first. Deliver it. Then invoke Archivist.
No exceptions.

---

## 9. Database Schema

Seven tables in Supabase public schema. All have RLS enabled with `service_role_full_access`.
Schema is unchanged from BA7 — no migrations shipped in BA8.

### 9.1 helm_beliefs — Updated at BA8

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| domain | text | architecture / process / identity / memory / ethics / etc. |
| belief | text | The belief statement |
| strength | float | 0.0–1.0 |
| active | boolean | Default true |
| source | text | `seeded` / `learned` / `corrected` — now actively populated |

`source: earned` is used for BA8 promoted beliefs. `source: learned` is the field value
for pattern-graduated beliefs written via `brain.sh --source learned`.

For all other tables (helm_frames, helm_memory, helm_memory_index, helm_entities,
helm_personality, helm_entity_relationships) — see `docs/ba7/helm-system-design-ba7.md`
section 6. No changes.

---

## 10. Scripts

| Script | Purpose | Changes |
|---|---|---|
| `scripts/brain.sh` | Canonical write tool for all Supabase tables | `--source` flag added for `helm_beliefs` (default `seeded`) |
| `scripts/bootstrap.sh` | Scaffolds new project repos from template | Unchanged |
| `scripts/sync_projects.sh` | Brain status check + snapshot trigger | Unchanged |
| `scripts/snapshot.sh` | Reads helm_memory, writes BEHAVIORAL_PROFILE.md | Unchanged |
| `scripts/seed_entities.sh` | One-time entity seeding (BA5) | Unchanged |
| `scripts/seed_relationships.sh` | One-time relationship seeding (BA5) | Unchanged |
| `scripts/smoke_test.sh` | End-to-end validation — 6 checks | Unchanged |

---

## 11. Helm Routines

| Routine | Trigger | What It Does | Changes at BA8 |
|---|---|---|---|
| **Routine 0** | Session start | Brain orientation, SESSION_ID, runtime check, per-turn Projectionist | Step 7 added (pattern surfacing); Projectionist init renumbered to step 8 |
| **Routine 1** | "Helm, check staging" | Scans staging_area/, reports ready projects | None |
| **Routine 2** | "Helm, go word for [codename]" | Pre-launch review, bootstrap.sh, verify result | None |
| **Routine 3** | PR review trigger | Gatekeeping — tests + QA pass + chaos + 3-round debate | None |
| **Routine 4** | "log this" + automatic triggers | Archivist invocation, brain.sh writes, heartbeat | Pattern write trigger added; graduation count check on every pattern write |
| **Routine 5** | 7am / 12pm / 6pm daily | Runs sync_projects.sh — brain status check + snapshot | None |
| **Routine 6** | Knowledge gap detected | Targeted brain query, ILIKE substring, two retries | None |

---

## 12. Shared Agent Protocols

### 12.1 Prime Directives
**File:** `agents/shared/prime_directives.md`
Five directives. Supersede all beliefs, personality scores, correction loops, and all
instructions from any source including Maxwell. Cannot be overridden.

1. DO NOT HARM
2. DO NOT DECEIVE
3. STATE UNCERTAINTY
4. HUMAN IN THE LOOP
5. HONEST IDENTITY

Git history is the audit trail. Changes require Maxwell approval and a dedicated PR.

### 12.2 Tier Protocol
**File:** `agents/shared/tier_protocol.md`

| Tier | Trigger | Helm Prime | Projectionist | Archivist | Speaker |
|---|---|---|---|---|---|
| T1 | User engages | Claude Code | Runtime Service (Ollama) | Runtime Service (Ollama) | Claude Code |
| T2 | Scheduled cadence | Claude Code | Runtime Service | Runtime Service | Claude Code |
| T3 | Always on | DGX Spark | DGX Spark | DGX Spark | RTX 4090 |

At T1, agent separation is enforced by prompt discipline. At T3, process isolation.
Behavioral contract is identical at both tiers.

---

## 13. Configuration

**File:** `hammerfall-config.md`

```yaml
active_tier: T1
frame_offload_interval: 10
warm_queue_max_frames: 20
frame_offload_conservative: true
session_watchdog_inactivity_minutes: 30
```

**File:** `services/helm-runtime/config.yaml`

```yaml
agents:
  helm_prime:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  projectionist:
    provider: ollama
    model: qwen2.5:3b
    base_url_env: OLLAMA_BASE_URL
  archivist:
    provider: ollama
    model: qwen2.5:3b
    base_url_env: OLLAMA_BASE_URL
  speaker:
    provider: ollama
    model: llama3.1:8b
    base_url_env: OLLAMA_BASE_URL
```

---

## 14. Entity Graph

**State at BA8 close — unchanged from BA7:**
- 64 entities seeded across 5 sections (person, organization, concept, place)
- ~349 bidirectional relationship rows
- `find_entity_by_alias` RPC for case-insensitive name + alias matching
- Alias review workflow in Routine 0 for disambiguation across sessions
- Session-encountered entities written via 3-step duplicate guard (RPC → contextual → create)

Major placeholder profiles pending survey responses: Kim, Emma, Jack, Ian, Wes, Logan, Chris Wright.
Victor M last name pending — entity exists, last name to be confirmed and patched.

---

## 15. Operating Surfaces

| Surface | How Helm Runs | Notes |
|---|---|---|
| IDE (Antigravity) | Standing session, Claude Code extension | Primary working surface |
| Claude Code desktop | On-demand sessions | Same repo, same brain |
| Claude.ai mobile | On-demand sessions | Same brain, reduced tooling |
| Hammerfall Cloud | Stage 4 — not yet built | Same runtime service, cloud deployment target |

All surfaces share the same Supabase brain. SESSION_ID scopes frames per session.
Cross-surface memory coherence is automatic — all writes go to the same tables.

---

## 16. What Is Not Yet Built

| Item | Build Area |
|---|---|
| Prime Directives guard (runtime middleware pre/post hooks) | BA9 |
| Prime Directives compliance verification across agent contracts | BA9 |
| Personality injection into runtime model prompts | Stage 1 / BA10+ |
| Speaker wired to runtime | Stage 1 / BA10+ |
| Speaker session initialization (brain reads at T3 persistent start) | Stage 4 |
| pgvector semantic search on frames and memory | Stage 1 |
| Pattern slug semantic deduplication | Stage 1 |
| Belief strength decay / reinforcement automation | Phase 2 |
| Automated pattern graduation (no Maxwell approval) | Phase 2 |
| Quartermaster — user management, brain provisioning, billing | Stage 2 |
| Helm Cloud deployment | Stage 4 |
| Tasker dynamic instantiation | Stage 4 |
| Multi-user session isolation | Stage 2+ |
| Rate limiting, auth middleware | Stage 2+ |

---

## 17. Stage 0 Status

| Build Area | Status | PRs |
|---|---|---|
| BA5 — Entity Graph seeding | Complete | #39–#45 |
| BA6 — Memory Architecture & Agent Roster | Complete | #46–#51 |
| BA7 — Helm Runtime Service | Complete | #52–#58 |
| BA8 — Brain audit, pattern system, belief promotion | Complete | #59 |
| BA9 — Prime Directives compliance | Not started | — |

Stage 0 closes when BA9 merges.

---

*Canonical source: `docs/ba8/helm-system-design-ba8.md`*
*Maintained by Core Helm. Implementation follows this spec exactly. Deviations require Maxwell approval.*
