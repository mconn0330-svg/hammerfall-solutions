# Helm System — Technical Design Specification
## State at BA7 Close

> **Historical document — frozen at the date below.** References to "Speaker" reflect the pre-Ambient Turn architecture. Speaker was deprecated in Lane C Phase 3 (PRs #78 code deletion, #79 contract archival, #80 reference scrub). Current architecture: `docs/founding_docs/Helm_The_Ambient_Turn.md`. Deprecation rationale: `docs/archive/speaker-deprecated/`.

**Version:** BA7 Close
**Date:** 2026-04-12
**Maintained by:** Core Helm — `agents/helm/helm_prompt.md`
**Previous:** `docs/ba6/helm-system-design-ba6.md`

---

## 1. System Overview

Helm is Maxwell's AI Chief of Staff and Technical Director. At BA7 close, the system
runs as a multi-agent, multi-model architecture: Helm Prime on Claude, Projectionist
and Archivist on local quantized models via the Helm Runtime Service. The shared
Supabase brain is the canonical memory store across all surfaces and agents.

**What changed in BA7:**
The Helm Runtime Service was added as the orchestration layer between Helm Prime and
its sub-agents. Projectionist and Archivist now execute on Qwen2.5 3B via Ollama —
not burning Claude API tokens on structured mechanical tasks. The Agent tool is
removed from the Projectionist/Archivist invocation path. Helm Prime calls the runtime
directly via bash curl in Routines 0 and 4.

**Core design principles (unchanged from BA6):**
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
**Owns:** Response generation, runtime invocation (Routines 0/4), belief-linked decisions
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
**Note:** Speaker session initialization (brain reads for `helm_personality` and
`helm_beliefs` at T3 session start as a persistent process) is not yet defined.
Architecture to be specified at Speaker wiring build area (Stage 4).

### 2.5 Taskers (Stage 4 — not yet implemented)
Scope-bound Helm instances for specific projects or tasks. Each is a full Helm stack
(Speaker + Projectionist + Archivist) operating within a bounded context. All write
to the same Supabase brain scoped by `project`/`agent` fields. Helm Prime creates
and prunes them dynamically at Stage 4.

---

## 3. Helm Runtime Service

**New in BA7.** The orchestration layer between Helm Prime and its sub-agents.

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

### 3.1 Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /invoke/{agent_role}` | Route request to configured model, run middleware pipeline, return response |
| `GET /health` | Service up + all model endpoints reachable + Supabase queryable |
| `GET /config/agents` | Current agent-to-model mapping — no secrets exposed |

### 3.2 Invocation Model

**Option B (confirmed):** Helm Prime calls the runtime directly via bash curl in
Routines 0 and 4. The Agent tool is removed from the Projectionist/Archivist path.
The runtime IS the coordination mechanism — not a subprocess behind it.

```
Claude Code (Helm Prime session)
  │
  │  Routine 0 — per-turn (after response delivered)
  │  [Bash tool: curl POST /invoke/projectionist]
  │
  │  Routine 4 — post-response writes
  │  [Bash tool: curl POST /invoke/archivist]
  │
  ▼
Helm Runtime Service (FastAPI :8000)
  │
  ├── Middleware pipeline
  ├── Model Router → LiteLLM
  │
  ├── → Ollama :11434 (Projectionist/Archivist — Qwen2.5 3B)
  └── → Supabase (helm_frames / helm_memory)
```

### 3.3 Request Schema

All `/invoke/{role}` requests use the same body:

```json
{
  "session_id": "uuid — generated by Claude Code at session start",
  "turn_number": 14,
  "user_message": "verbatim user message — no truncation",
  "helm_response": "verbatim Helm Prime response — no truncation",
  "context": { "project": "hammerfall-solutions", "agent": "helm" }
}
```

The runtime is stateless. All session context is caller-supplied per-request.
SESSION_ID generated by Claude Code (`crypto.randomUUID()`) and passed on every call.

### 3.4 Middleware Pipeline

```
Request enters
  → [Pre]  session_context_inject  — ACTIVE: injects session_id, turn_number, project
  → [Pre]  personality_inject      — STUB: BA8 (load helm_personality into prompt)
  → [Pre]  prime_directives_guard  — STUB: BA9 (validate request pre-model call)
  → Model call via LiteLLM
  → [Post] output_validator        — ACTIVE: validates Projectionist JSON schema
  → [Post] prime_directives_output — STUB: BA9 (scan output for PD violations)
Response exits
```

Stub hooks are pass-through only. No implementation. Scaffolded for BA8/BA9.

### 3.5 Provider Types

| Provider | Use Case | Required Config |
|---|---|---|
| `anthropic` | Helm Cloud default, BYO Claude key | `api_key_env` |
| `openai` | BYO OpenAI key | `api_key_env` |
| `ollama` | Local dev, Helm Self-Hosted | `base_url_env` |
| `custom` | Any OpenAI-compatible endpoint | `base_url_env`, optional `api_key_env` |

**BYO model contract:** Swapping any agent's model is one line in `config.yaml` +
service restart. No code changes. Config validated at startup via Pydantic schema —
malformed config produces a named error before the service accepts requests.

### 3.6 Health Check Caching

Model health checks are cached per-role for 60 seconds. Paid provider endpoints
(Anthropic, OpenAI) are not pinged on every `/health` call. Monitoring loops,
smoke tests, and Quartermaster polling do not accumulate API costs.

---

## 4. Memory Architecture

Three layers. Each fills and passes down. Nothing compresses. Nothing is lost.

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

### 4.1 Frame Format

```json
{
  "turn": 14,
  "timestamp": "2026-04-12T14:32:11Z",
  "user_id": "maxwell",
  "session_id": "uuid",
  "user": "[verbatim user message]",
  "helm": "[verbatim Helm Prime response]",
  "topic": "[inferred topic]",
  "domain": "architecture | process | people | ethics | decisions | other",
  "entities_mentioned": ["Maxwell", "BA7"],
  "belief_links": ["pipeline-serves-product"],
  "frame_status": "active | superseded | canonical",
  "superseded_reason": null,
  "superseded_at_turn": null
}
```

### 4.2 Two Offload Triggers

**Batch trigger (priority):** Fires when warm queue reaches `warm_queue_max_frames` (20).
Full batch offload — all warm frames pass to Archivist immediately. No conservative %.

**Interval trigger (steady-state):** Fires every `frame_offload_interval` turns (10).
When `frame_offload_conservative: true`, fires at 80% of interval (turn 8, 16, 24...).
Oldest warm frame passes to Archivist.

### 4.3 Two-Path Recall

**Path A (new frames):** Enter `helm_frames` as normal. Conveyor applies.

**Path B (recalled frames):** Projectionist queries `helm_memory` directly.
Frame served to Helm Prime in-context. Never written back to `helm_frames`.
Recalled frames are read-only — already exist in `helm_memory` at full fidelity.

### 4.4 Write Path Summary

| Write Type | Tool | Table |
|---|---|---|
| Frame creation | `supabase_client.py` (via runtime) | `helm_frames` |
| Frame migration summary + full content | `supabase_client.py` (via runtime) | `helm_memory` |
| Behavioral / correction / reasoning / entity | `brain.sh` (shell context) | `helm_memory` / other |
| Beliefs | `brain.sh` | `helm_beliefs` |
| Entities | `brain.sh` | `helm_entities` |
| Personality scores | `brain.sh` | `helm_personality` |
| Relationships | `brain.sh` | `helm_entity_relationships` |

---

## 5. Session Flow

### 5.1 Session Start (Routine 0)

1. Read `COMPANY_BEHAVIOR.md`, `BEHAVIORAL_PROFILE.md`, `active-projects.md`, `hammerfall-config.md`
2. Record SESSION_START_COUNT (brain row count query)
3. Read `helm_memory_index` — know what categories exist
4. Pull last 5 behavioral entries + active `[CORRECTION]` entries
5. Read active beliefs (strength descending) + personality scores
6. Check pending alias reviews — surface if any
7. Generate SESSION_ID (`crypto.randomUUID()`), initialize TURN_COUNT=0
8. Read frame offload config from `hammerfall-config.md`
9. **Runtime connectivity check** — `GET /health`, log `[RUNTIME-UNAVAILABLE]` if unreachable, continue

### 5.2 Per-Turn (after every response)

1. Increment TURN_COUNT
2. Delta check — count query against brain; if new entries exist, pull and absorb
3. Call `POST /invoke/projectionist` via bash curl (temp file pattern)
4. Every 5 messages — delta check regardless of Maxwell cadence

### 5.3 Post-Response Writes (Routine 4)

1. Complete response, deliver to Maxwell
2. Note any write triggers that fired during reasoning
3. Call `POST /invoke/archivist` via bash curl — drains all `layer='cold'` frames
4. Execute any `brain.sh` writes for behavioral/correction/reasoning/entity entries

### 5.4 Session End

1. Call `POST /invoke/projectionist` with `resolution_pass: true` — marks canonical/superseded
2. Call `POST /invoke/archivist` — final cold frame drain
3. Transfer scratchpad to BEHAVIORAL_PROFILE.md, flush scratchpad

### 5.5 Curl Pattern (temp file — all runtime calls)

```bash
# USER_MSG and HELM_MSG set as env vars before this block
PROJ_TMPFILE=$(mktemp /tmp/proj_req_XXXXXX.json)
node -e "
  const body = {
    session_id: process.env.SESSION_ID,
    turn_number: parseInt(process.env.TURN_COUNT),
    user_message: process.env.USER_MSG,
    helm_response: process.env.HELM_MSG,
    context: { project: 'hammerfall-solutions', agent: 'helm' }
  };
  process.stdout.write(JSON.stringify(body));
" > "$PROJ_TMPFILE"
curl -s -X POST http://localhost:8000/invoke/projectionist \
  -H "Content-Type: application/json" \
  -d @"$PROJ_TMPFILE"
rm -f "$PROJ_TMPFILE"
```

Node reads content via `process.env`, handles all escaping via `JSON.stringify`.
Never inline shell interpolation for message content — breaks on quotes and newlines.

---

## 6. Database Schema

Seven tables in Supabase public schema. All have RLS enabled with `service_role_full_access`.

### 6.1 helm_frames (Projectionist transient workspace)

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK, default gen_random_uuid() |
| session_id | uuid | Session identifier — generated by Claude Code |
| turn_number | integer | Turn within session |
| layer | text | `hot` / `warm` / `cold` |
| frame_json | jsonb | Complete frame — verbatim turn + metadata |
| frame_status | text | `active` / `superseded` / `canonical` — authoritative |
| created_at | timestamptz | Default now() |

UNIQUE(session_id, turn_number) — rejects duplicate writes at DB layer.
Three indexes: (session_id, turn_number), layer, session_id.

**frame_status is authoritative in the column.** The field inside `frame_json` must
match via atomic PATCH — both updated in a single write, never one without the other.

### 6.2 helm_memory (Archivist cold store)

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| project | text | e.g. `hammerfall-solutions` |
| agent | text | e.g. `helm` |
| memory_type | text | `behavioral` / `scratchpad` / `reasoning` / `heartbeat` / `frame` |
| content | text | Summary — fast hot/warm retrieval |
| full_content | jsonb | Photographic layer — complete verbatim frame or context |
| confidence | float | Reasoning entries only (0.0–1.0) |
| session_date | date | Extracted from frame timestamp (`[:10]`) — Stage 1 filter field |
| sync_ready | boolean | Default false |
| synced_to_core | boolean | Default false |
| created_at | timestamptz | Default now() |

### 6.3 helm_memory_index (Category table of contents)

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| project | text | |
| agent | text | |
| category | text | |
| summary | text | 2-3 sentences — what belongs in this category |
| entry_count | integer | |
| date_range_start / end | date | |
| last_updated | timestamptz | |

UNIQUE(project, agent, category). Seven seed categories for hammerfall-solutions/helm:
architecture, environment, decisions, people, projects, patterns, north_stars.

### 6.4 helm_beliefs

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| domain | text | architecture / process / people / ethics / etc. |
| belief | text | The belief statement |
| strength | float | 0.0–1.0 |
| active | boolean | Default true |
| source | text | `seeded` / `learned` / `corrected` |

### 6.5 helm_entities

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| entity_type | text | `person` / `place` / `organization` / `concept` |
| name | text | Canonical name |
| aliases | jsonb | Array of alternate names |
| summary | text | One-sentence plain-text description |
| attributes | jsonb | Flexible — source, known_at_time, needs_alias_review, etc. |
| active | boolean | Default true |

RPC `find_entity_by_alias(search_name)` — case-insensitive name + alias match.

### 6.6 helm_personality

| Column | Type | Notes |
|---|---|---|
| attribute | text | UNIQUE — one row per attribute |
| score | float | 0.0–1.0 |
| description | text | What this score means in practice |

Upsert via `ON CONFLICT(attribute) DO UPDATE`.

### 6.7 helm_entity_relationships

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| from_entity | uuid | FK → helm_entities |
| to_entity | uuid | FK → helm_entities |
| relationship | text | Label (e.g. `friend`, `colleague`, `family`) |
| notes | text | Relationship context |
| strength | float | 0.0–1.0 |
| active | boolean | Default true |

Bidirectional — two rows per relationship (A→B and B→A).

---

## 7. Scripts

| Script | Purpose |
|---|---|
| `scripts/brain.sh` | Canonical write tool for Claude Code shell contexts. Writes to all Supabase tables. PATCH support for helm_entities. |
| `scripts/bootstrap.sh` | Scaffolds new project repos from template. Clones Core Helm at point-in-time. |
| `scripts/sync_projects.sh` | Brain status check + snapshot trigger. Queries last 20 brain entries, triggers snapshot.sh. |
| `scripts/snapshot.sh` | Reads helm_memory behavioral entries, writes to `BEHAVIORAL_PROFILE.md`, commits. |
| `scripts/seed_entities.sh` | One-time seeding of 64 entities across 5 sections into helm_entities. |
| `scripts/seed_relationships.sh` | One-time seeding of ~349 bidirectional relationship rows into helm_entity_relationships. |
| `scripts/smoke_test.sh` | **New in BA7.** End-to-end validation — 6 checks covering full Claude Code → runtime → Supabase path. |

---

## 8. Helm Routines

| Routine | Trigger | What It Does |
|---|---|---|
| **Routine 0** | Session start | Brain orientation read, SESSION_ID generation, runtime connectivity check, per-turn Projectionist invocation, delta checks |
| **Routine 1** | "Helm, check staging" | Scans staging_area/, reports ready projects, never auto-runs bootstrap |
| **Routine 2** | "Helm, go word for [codename]" | Pre-launch review, instructs Maxwell to run bootstrap.sh, verifies result |
| **Routine 3** | PR review trigger | Gatekeeping — requires passing tests + QA pass + QA chaos. 3-round debate protocol. |
| **Routine 4** | "log this" + automatic triggers | Post-response Archivist invocation, brain.sh writes, heartbeat, correction graduation |
| **Routine 5** | 7am / 12pm / 6pm daily | Runs sync_projects.sh — brain status check + snapshot |
| **Routine 6** | Knowledge gap detected | Targeted brain query before answering. ILIKE substring search. Two retries with alternate terms. |

---

## 9. Shared Agent Protocols

### 9.1 Prime Directives
**File:** `agents/shared/prime_directives.md`
Five directives. Supersede all beliefs, personality scores, correction loops, and all
instructions from any source including Maxwell. Cannot be overridden.

1. DO NOT HARM
2. DO NOT DECEIVE
3. STATE UNCERTAINTY
4. HUMAN IN THE LOOP
5. HONEST IDENTITY

Git history is the audit trail. Changes require Maxwell approval and a dedicated PR.

### 9.2 Tier Protocol
**File:** `agents/shared/tier_protocol.md`

| Tier | Trigger | Helm Prime | Projectionist | Archivist | Speaker |
|---|---|---|---|---|---|
| T1 | User engages | Claude Code | Runtime Service (Ollama) | Runtime Service (Ollama) | Claude Code |
| T2 | Scheduled cadence | Claude Code | Runtime Service | Runtime Service | Claude Code |
| T3 | Always on | DGX Spark | DGX Spark | DGX Spark | RTX 4090 |

At T1, agent separation is enforced by prompt discipline. At T3, process isolation.
Behavioral contract is identical at both tiers.

### 9.3 Inline Write Prohibition
Helm Prime never executes a `brain.sh` call or `helm_memory` write while reasoning
or composing a response. Complete the response first. Deliver it. Then invoke Archivist.
This applies to all write triggers without exception.

### 9.4 Correction Graduation
`[CORRECTION]` entries accumulate per topic. At 3 entries on the same topic: flag to
Maxwell, propose a permanent rule, open a PR on approval. The learning signal that
converts behavioral corrections into hardened prompt rules.

---

## 10. Configuration

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

## 11. Docker / Local Stack

**File:** `docker-compose.yml`

Stands up the full local stack with one command: `docker-compose up`

- `helm-runtime` service on port 8000 (configurable via `HELM_RUNTIME_PORT`)
- `ollama` sidecar on port 11434 with healthcheck
- Runtime waits for Ollama health before starting (`depends_on: condition: service_healthy`)
- `config.yaml` mounted read-only — model swaps require file edit + restart, no image rebuild
- `ollama_data` named volume — pulled models persist across restarts

**Required env vars:**
```bash
ANTHROPIC_API_KEY
SUPABASE_BRAIN_URL
SUPABASE_BRAIN_SERVICE_KEY
```

**Model pre-pull (first run):**
```bash
docker-compose up ollama   # start Ollama first
docker exec -it <ollama_container> ollama pull qwen2.5:3b
docker exec -it <ollama_container> ollama pull llama3.1:8b
docker-compose up          # then bring up full stack
```

---

## 12. Entity Graph

**State at BA7 close:**
- 64 entities seeded across 5 sections (person, organization, concept, place)
- ~349 bidirectional relationship rows
- `find_entity_by_alias` RPC for case-insensitive name + alias matching
- Alias review workflow in Routine 0 for disambiguation across sessions
- Session-encountered entities written via 3-step duplicate guard (RPC → contextual → create)

Major placeholder profiles pending survey responses: Kim, Emma, Jack, Ian, Wes, Logan, Chris Wright.
Victor M last name pending — entity exists, last name to be confirmed and patched.

---

## 13. Operating Surfaces

| Surface | How Helm Runs | Notes |
|---|---|---|
| IDE (Antigravity) | Standing session, Claude Code extension | Primary working surface |
| Claude Code desktop | On-demand sessions | Same repo, same brain |
| Claude.ai mobile | On-demand sessions | Same brain, reduced tooling |
| Hammerfall Cloud | Stage 4 — not yet built | Same runtime service, cloud deployment target |

All surfaces share the same Supabase brain. SESSION_ID scopes frames per session.
Cross-surface memory coherence is automatic — all writes go to the same tables.

---

## 14. What Is Not Yet Built

| Item | Build Area |
|---|---|
| Prime Directives guard (runtime middleware pre/post hooks) | BA9 |
| Personality injection into runtime model prompts | BA8 |
| Self-migration audit (north_stars, patterns review) | BA8 |
| Prime Directives compliance verification across agent contracts | BA9 |
| Speaker wired to runtime | Stage 1 / BA10+ |
| Speaker session initialization (brain reads at T3 persistent start) | Stage 4 |
| pgvector semantic search on frames and memory | Stage 1 |
| Quartermaster — user management, brain provisioning, billing, product surface | Stage 2 |
| Helm Cloud deployment (actual cloud infrastructure) | Stage 4 |
| Tasker dynamic instantiation (Stage 4 orchestration pattern) | Stage 4 |
| Multi-user session isolation | Stage 2+ |
| Rate limiting, auth middleware | Stage 2+ |
| BA7 model swap validation (confirm custom provider end-to-end) | Ongoing |

---

## 15. Stage 0 Status

| Build Area | Status | PRs |
|---|---|---|
| BA5 — Entity Graph seeding | Complete | #33–#45 |
| BA6 — Memory Architecture & Agent Roster | Complete | #44–#50 |
| BA7 — Helm Runtime Service | Complete | #52–#57 |
| BA8 — Self-migration audit | Not started | — |
| BA9 — Prime Directives compliance | Not started | — |

Stage 0 closes when BA8 and BA9 are merged.

---

*Canonical source: `docs/ba7/helm-system-design-ba7.md`*
*Maintained by Core Helm. Implementation follows this spec exactly. Deviations require Maxwell approval.*
