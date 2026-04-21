# Helm System — Technical Design Specification
## State at BA6 Close

**Version:** BA6 Close
**Date:** 2026-04-11
**Maintained by:** Core Helm — `agents/helm/helm_prompt.md`

---

## 1. System Overview

Helm is Maxwell's AI Chief of Staff and Technical Director. The system is a multi-surface,
multi-agent architecture built on Claude Code (T1) with a shared Supabase brain as the
canonical memory store. All agents are subdivisions of Helm — the same identity,
maximally specialized. One brain. One identity. Accessed from any surface.

**Core design principles:**
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
**Purpose:** Central identity and orchestrator. Strategic reasoning, belief-linked decisions,
all significant responses. The real Helm. Directs sub-agents post-response.
**Owns:** Response generation, orchestrating Speaker/Projectionist/Archivist, belief-linked decisions
**Never:** Writes memory inline while reasoning. Handles context logistics.

### 2.2 Projectionist
**File:** `agents/helm/projectionist/projectionist.md`
**Lives:** Claude Code Agent tool (T1) / DGX Spark persistent process (T3)
**Purpose:** Warm memory and frame manager. Captures every turn as a structured frame,
manages the warm queue conveyor, offloads to Archivist, handles cold recall.
**Owns:** Frame creation, metadata inference, session_id tracking, warm queue in `helm_frames`,
offload trigger evaluation, inline pivot detection, session-end resolution, cold recall (Path B)
**Never:** Strategic reasoning. Brain writes to `helm_memory`. Re-enters recalled frames into conveyor.

### 2.3 Archivist
**File:** `agents/helm/archivist/archivist.md`
**Lives:** Claude Code Agent tool (T1) / DGX Spark persistent process (T3)
**Purpose:** Cold storage and full-fidelity writes. Owns all `helm_memory` writes.
Migrates frames from `helm_frames` to `helm_memory` at full fidelity. Never on critical path.
**Owns:** All `helm_memory` writes, frame migration, `[REASONING]`/`[CORRECTION]`/`[NEW-ENTITY]`
entries, relationship writes, cold recall response to Projectionist
**Never:** Context management. Response path involvement.
**Write path guarantee:** Always `brain.sh → Supabase` regardless of model executing the role.

### 2.4 Speaker
**File:** `agents/helm/speaker/speaker.md`
**Lives:** Claude Code (T1) / RTX 4090 (T3)
**Purpose:** Permanent surface-facing voice agent. Always travels with Helm Prime.
The real-time conversation layer — low latency, routes complex requests up to Helm Prime.
**Owns:** Request classification (simple → resolve, complex → route), response streaming,
session event bus, integration monitoring (T2+)
**Never:** Strategic reasoning. Memory writes. Context management.

### 2.5 Taskers (Stage 4 — not yet implemented)
**Future file:** Per-instance `tasker.md`
**Purpose:** Scope-bound Helm instances for specific projects or tasks. Each is a full
Helm stack (Speaker + Projectionist + Archivist) operating within a bounded context.
All write to the same Supabase brain, scoped by `project`/`agent` fields. Helm Prime
creates and prunes them dynamically. The IDE Helm is a manually-created example of
what a Tasker will look like when the pattern is operational.

---

## 3. Memory Architecture

Three layers. Each fills and passes down. Nothing compresses. Nothing is lost.

```
HOT — Helm Prime + Speaker
  Context window — current session turns
  When limit approaches → oldest frame passes to Projectionist
  Zero retrieval cost for current session

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
  Superseded queryable explicitly ("what did we rule out")
```

### 3.1 Frame Format

One frame = one complete turn. Projectionist creates it. Metadata fields are Stage 1
pgvector embedding anchors.

```json
{
  "turn": 14,
  "timestamp": "2026-04-11T14:32:11Z",
  "user_id": "maxwell",
  "session_id": "uuid",
  "user": "[verbatim user message — no truncation]",
  "helm": "[verbatim Helm Prime response — no truncation]",
  "topic": "[inferred — project codename or topic area]",
  "domain": "[inferred — architecture / process / people / ethics / etc]",
  "entities_mentioned": ["Maxwell", "Labcorp", "BA6"],
  "belief_links": ["pipeline-serves-product", "simplicity-first"],
  "frame_status": "active",
  "superseded_reason": null,
  "superseded_at_turn": null
}
```

**frame_status lifecycle:**
- `active` — default. Current session, not yet resolved.
- `superseded` — approach abandoned. `superseded_reason` required. Stored as negative example.
- `canonical` — final decided path. Set by session-end resolution pass.

**Atomic PATCH rule:** When Projectionist updates `frame_status`, both the column and the
`frame_json` field must be updated in a single PATCH. The column is authoritative for queries.

### 3.2 Two-Path Recall

**Path A (new frames):** Enter `helm_frames` → conveyor → Archivist → `helm_memory`

**Path B (recalled frames):** Projectionist queries `helm_memory` directly → frame served
to Helm Prime in-context → never written to `helm_frames`. No duplicate risk.

### 3.3 Offload Triggers

**Batch trigger (priority):** Fires at exactly `warm_queue_max_frames` (default: 20).
Full batch offload. Takes priority over interval trigger. No conservative percentage.

**Interval trigger (steady-state):** Fires every `frame_offload_interval` turns (default: 10).
When `frame_offload_conservative: true`, fires at 80% of the interval. Oldest frame passes down.

---

## 4. Database Schema

All tables live in the Supabase Brain project (`zlcvrfmbtpxlhsqosdqf`).
RLS enabled on all tables. `service_role_full_access` policy on each.

### 4.1 helm_memory — Long-Term Authoritative Store
```
id              UUID        PK
project         TEXT        project scoping (e.g. "hammerfall-solutions")
agent           TEXT        agent slug (e.g. "helm")
memory_type     TEXT        CHECK: behavioral, scratchpad, archive, sync, monologue,
                            coherence_check, external_knowledge, reasoning, heartbeat, frame
content         TEXT        summary / primary content
full_content    JSONB       photographic layer — verbatim frame JSON or decision detail
confidence      FLOAT       reasoning entries only (0.0–1.0)
sync_ready      BOOLEAN     pending sync to Core Helm
synced_to_core  BOOLEAN     sync complete flag
session_date    DATE        date of session
created_at      TIMESTAMPTZ
```
Indexes: project, sync_ready (partial), (project, agent, memory_type)

### 4.2 helm_memory_index — Brain Table of Contents
```
id              UUID        PK
project         TEXT
agent           TEXT
category        TEXT        e.g. "architecture", "decisions", "people"
summary         TEXT        2-3 sentences — what belongs in this category
entry_count     INT
date_range_start DATE
date_range_end   DATE
last_updated    TIMESTAMPTZ
UNIQUE(project, agent, category)
```

### 4.3 helm_frames — Projectionist Transient Workspace
```
id              UUID        PK
session_id      UUID        session identifier
turn_number     INT         turn within session
layer           TEXT        CHECK: hot, warm, cold
frame_json      JSONB       complete frame payload
frame_status    TEXT        CHECK: active, superseded, canonical
created_at      TIMESTAMPTZ
UNIQUE(session_id, turn_number)
```
Indexes: (session_id, turn_number) composite, layer, session_id

**Lifecycle:** Archivist deletes rows immediately after migrating to `helm_memory`.
`helm_frames` is transient — near-empty between sessions.

### 4.4 helm_beliefs — Helm's Operating Worldview
```
id          UUID    PK
domain      TEXT    e.g. "architecture", "process", "people", "ethics"
belief      TEXT    the belief statement
strength    FLOAT   0.0–1.0 (default 0.7)
active      BOOLEAN
source      TEXT    "seeded" / "learned" / "corrected"
created_at  TIMESTAMPTZ
```

### 4.5 helm_entities — Knowledge Graph Nodes
```
id           UUID     PK
entity_type  TEXT     person, place, organization, concept
name         TEXT
attributes   JSONB    flexible metadata (occupation, notes, needs_alias_review, etc.)
aliases      TEXT[]   GIN-indexed array of alternate names/nicknames
summary      TEXT     one-sentence plain-text description
active       BOOLEAN
first_seen   TIMESTAMPTZ
last_updated TIMESTAMPTZ
```
**Current state:** 64 entities seeded (BA5) — Maxwell, family, friends, places, organizations.
Major placeholder profiles (Kim, Emma, Jack, Ian, Wes, Logan, Chris Wright) pending survey responses.

### 4.6 helm_entity_relationships — Knowledge Graph Edges
```
id              UUID    PK
from_entity     UUID    FK → helm_entities
to_entity       UUID    FK → helm_entities
relationship    TEXT    spouse, parent, child, sibling, friend, colleague, employee,
                        founder, member, resident, origin, owner, pet, pseudo_family,
                        grandparent, grandchild, uncle, niece, engaged, supervisor,
                        direct_report, workplace
notes           TEXT    context (step/in-law, dates, detail)
active          BOOLEAN
strength        FLOAT   optional 0.0–1.0
created_at      TIMESTAMPTZ
CONSTRAINT no_self_relationship CHECK (from_entity <> to_entity)
```
**Current state:** 349 rows — bidirectional pairs for all 64 entities.

### 4.7 helm_personality — Six Communication Attributes
```
id          UUID    PK
attribute   TEXT    UNIQUE — directness, verbosity, sarcasm, formality,
                    challenge_frequency, show_reasoning
score       FLOAT   0.0–1.0
description TEXT
created_at  TIMESTAMPTZ
updated_at  TIMESTAMPTZ
```
Upserts on `attribute` (ON CONFLICT — only one row per attribute).

---

## 5. Postgres Functions (RPCs)

### 5.1 find_entity_by_alias(search_name TEXT)
**Migration:** `006_add_find_entity_by_alias_rpc.sql`
**Purpose:** Case-insensitive entity lookup by name or alias. Solves PostgREST `cs.{}` case-sensitivity limitation.
```sql
SELECT * FROM helm_entities
WHERE LOWER(name) = LOWER(search_name)
OR EXISTS (
  SELECT 1 FROM unnest(aliases) AS a
  WHERE LOWER(a) = LOWER(search_name)
);
```
Called via: `POST /rest/v1/rpc/find_entity_by_alias?active=eq.true` with `{"search_name":"..."}`

---

## 6. Scripts

### 6.1 brain.sh — Memory Write Helper
**File:** `scripts/brain.sh`
**Purpose:** All writes to the Supabase brain go through this script. Never write directly to `helm_memory` tables without it (except the Archivist frame migration which uses curl directly for performance).

**Supported tables:** `helm_memory`, `helm_beliefs`, `helm_entities`, `helm_personality`, `helm_entity_relationships`

**Key flags:**
- `--table TABLE` — target table (default: helm_memory)
- `--full-content JSON` — photographic memory layer for helm_memory
- `--confidence FLOAT` — reasoning entries
- `--aliases JSON` — array for helm_entities
- `--summary TEXT` — one-sentence description for helm_entities
- `--patch-id UUID` — switches helm_entities to PATCH (dynamic payload)
- `--attributes JSON` — JSONB for helm_entities
- `--from-entity / --to-entity UUID` — required for helm_entity_relationships
- `--rel-notes TEXT / --rel-strength FLOAT` — relationship context
- `--score FLOAT` — required for helm_personality

**Encoding:** All string content escaped via Node.js `JSON.stringify` with trailing `\r\n` stripped — guards against Windows/Git Bash heredoc newline injection.
**Fallback:** On `helm_memory` write failure, appends to `agents/$AGENT/memory/BEHAVIORAL_PROFILE.md`.

### 6.2 session_watchdog.sh
**File:** `scripts/session_watchdog.sh`
**Purpose:** Background sidecar. Monitors session inactivity. Flushes scratchpad to brain on timeout (default: 30 minutes) or shell close.

### 6.3 ping_session.sh
**File:** `scripts/ping_session.sh`
**Purpose:** Called after every Helm response. Increments message counter. At message 10 writes a mandatory heartbeat entry to the brain and resets counter to 0.

### 6.4 activity_ping.sh
**File:** `scripts/activity_ping.sh`
**Purpose:** Resets the watchdog inactivity timer without incrementing message counter. Called before long-running tool use or bash operations to prevent mid-task scratchpad flush.

### 6.5 sync_projects.sh
**File:** `scripts/sync_projects.sh`
**Purpose:** Brain status check and snapshot trigger. Queries recent brain activity across all projects, prints a summary, triggers `snapshot.sh`. Runs at 7AM, 12PM, 6PM daily and on "Helm, sync now."

### 6.6 snapshot.sh
**File:** `scripts/snapshot.sh`
**Purpose:** Reads all behavioral entries for a project/agent from the brain and writes them to `agents/$AGENT/memory/BEHAVIORAL_PROFILE.md` as a point-in-time snapshot. The .md file is a read-only snapshot — the brain is authoritative.

### 6.7 seed_entities.sh
**File:** `scripts/seed_entities.sh`
**Purpose:** One-time seed of 64 entities into `helm_entities`. 3-state safety guard. Not re-run after BA5 — entities are updated via brain.sh `--patch-id`.

### 6.8 seed_relationships.sh
**File:** `scripts/seed_relationships.sh`
**Purpose:** One-time seed of 349 bidirectional relationship rows into `helm_entity_relationships`. 3-state safety guard (EXPECTED_TOTAL=349).

### 6.9 patch_entity_summaries.sh
**File:** `scripts/patch_entity_summaries.sh`
**Purpose:** One-time data fix. Stripped trailing `\n` from all 64 entity names and populated summary column. Idempotent. Not re-run after BA5.

### 6.10 seed_beliefs.sh
**File:** `scripts/seed_beliefs.sh`
**Purpose:** Seeds Helm's initial belief set into `helm_beliefs`. Run once at BA2.

---

## 7. Helm Routines

Routines are named behavioral protocols embedded in `helm_prompt.md`. They fire on triggers.

### Routine 0 — Brain Read Protocol
**Trigger:** Session start — always runs first.

**Steps:**
1. Record `SESSION_START_COUNT` and `SESSION_START_TIMESTAMP`
2. Read `helm_memory_index` — know what categories exist
3. Pull last 5 behavioral entries for orientation
4. Pull active `[CORRECTION]` entries — absorb before beliefs
5. Read active beliefs ordered by strength descending
6. Read personality scores ordered by attribute ascending
7. Check `needs_alias_review` entities — surface before first substantive response
8. **Projectionist initialization:**
   - Generate `SESSION_ID` via `process.stdout.write(require('crypto').randomUUID())`
   - Initialize `TURN_COUNT=0`
   - Read frame offload parameters from `hammerfall-config.md`
   - T2 only: pre-load last session frames in turn order

**Per-turn (post-response):** Invoke Projectionist via Agent tool. Invoke Archivist for any queued writes.
**Session-end:** Projectionist resolution pass (canonical/superseded classification), Archivist flush.
**Delta check:** Before every response, count query. Pull delta if new entries exist. Every 5 messages regardless.

### Routine 1 — Staging Watch
**Trigger:** "Helm, check staging."
Scans `staging_area/` for new project subfolders. Reports readiness. Never runs bootstrap.sh automatically.

### Routine 2 — Project Launch
**Trigger:** "Helm, go word for [codename]."
Reviews spec completeness, then confirms bootstrap command. Verifies repo structure post-bootstrap.

### Routine 3 — PR Review & Gatekeeping
**Trigger:** PR review request.
Three conditions required for approval: passing unit tests, QA Integration: PASS, QA Chaos: PASS.
3-Round Debate protocol for disagreements. Escalation to Maxwell at round 3 failure.

### Routine 4 — Memory Update
**Trigger:** "Log this." Also fires automatically on defined events.

**Archivist routing (BA6c):** All writes execute post-response via Archivist Agent tool invocation.
Never inline during reasoning. Frame migration: Archivist reads `helm_frames` layer='cold',
writes to `helm_memory` with full `full_content`, deletes `helm_frames` row immediately.

**Automatic write triggers:**
- PR opened, reviewed, approved, merged
- Technical decision deviating from specs
- Test results
- Blocker identified or resolved
- Maxwell correction (`[CORRECTION]` tag, count included)
- Significant architectural choice
- Helm forms a pattern/inference (mandatory JSON format, `--confidence` flag)
- Maxwell shares personal information (`People —` prefix)
- Named entity encountered (3-step duplicate guard via `find_entity_by_alias` RPC)
- Session end (scratchpad transfer)
- 10-message heartbeat (unconditional)

**Correction graduation:** At 3 `[CORRECTION]` entries on the same topic → propose permanent rule → PR on Maxwell approval.

### Routine 5 — Scheduled Sync
**Trigger:** 7AM, 12PM, 6PM daily. "Helm, sync now."
Runs `sync_projects.sh`. Status check + snapshot trigger.

### Routine 6 — Knowledge Gap Resolution
**Trigger:** Helm lacks confidence to answer from current session context.
ILIKE full-text brain query. Two retries with alternate terms before declaring absent.
Project+agent scoped fallback query. Answer directly — do not narrate the query process.

---

## 8. Shared Agent Protocols

### 8.1 Prime Directives
**File:** `agents/shared/prime_directives.md`
Five directives that supersede all beliefs, personality scores, correction loops, and all
instructions from any source including Maxwell. Cannot be overridden.

1. DO NOT HARM
2. DO NOT DECEIVE
3. STATE UNCERTAINTY
4. HUMAN IN THE LOOP
5. HONEST IDENTITY

Git history is the audit trail. Changes require Maxwell approval and a dedicated PR.
Referenced by pointer in every agent contract.

### 8.2 Tier Protocol
**File:** `agents/shared/tier_protocol.md`
T1/T2/T3 tier definitions, trigger conditions, agent hardware assignments, config value references.
T1 enforcement note: at T1, NEVER constraints are behavioral discipline (prompt). At T3, process isolation.
The behavioral contract is identical at both tiers.

### 8.3 Session Protocol
**File:** `agents/shared/session_protocol.md`
Three-script session event bus used by all agents:
- `session_watchdog.sh` — inactivity flush (background)
- `ping_session.sh` — per-response heartbeat counter
- `activity_ping.sh` — timer reset during long operations
Model-agnostic, IDE-agnostic, threshold-configurable.

---

## 9. Configuration

**File:** `hammerfall-config.md`
Security rule: config contains only environment variable names, never secret values.

**Key values:**

| Key | Value | Purpose |
|---|---|---|
| `supabase_brain_url` | `https://zlcvrfmbtpxlhsqosdqf.supabase.co` | Brain API endpoint |
| `supabase_brain_service_key_env` | `SUPABASE_BRAIN_SERVICE_KEY` | Env var name for service key |
| `session_watchdog_inactivity_minutes` | `30` | Inactivity threshold |
| `active_tier` | `T1` | Current tier |
| `frame_offload_interval` | `10` | Interval trigger: turns between offloads |
| `warm_queue_max_frames` | `20` | Batch trigger: max warm frames before flush |
| `frame_offload_conservative` | `true` | Interval fires at 80% when true |

---

## 10. Entity Graph (BA5)

**64 entities** across 5 types: person (33), place (22), organization (6), pet (3).
**349 relationship rows** — bidirectional pairs with notes and optional strength scores.

**Seeded aliases (10 entities):** Maxwell Connolly, Kimberly Connolly, Emma Connolly,
Ian Connolly, Wesley Green, Logan Whitaker, Gregory Sharkey, Jack Connolly,
Jennifer Connolly, Amy Connolly.

**Pending:** Victor M last name unknown. 7 major placeholder profiles awaiting survey responses.
`profile_complete: false` attribute flags these for enrichment.

**Duplicate guard (Routine 4 step):**
1. RPC call `find_entity_by_alias` — case-insensitive name + alias match
2. If no match: contextual reasoning for nicknames/diminutives
3. Likely match → confirmation prompt. Uncertain → `needs_alias_review: true` tag.

---

## 11. Operating Surfaces

| Surface | Description | Current |
|---|---|---|
| Claude Code (IDE / Antigravity) | Primary build and development session | Active |
| Claude Code (Desktop) | Mobile/desktop standing access | Active |
| Claude Code (Web) | Browser-based access | Active |
| Spark (T3) | DGX Spark — Helm Prime + Projectionist + Archivist | Future (Stage 4) |
| RTX 4090 (T3) | Speaker — surface-facing low latency | Future (Stage 4) |

All surfaces connect to the same Supabase brain. Context is portable — no surface-specific state.

---

## 12. What Is Not Yet Built

| Item | Target |
|---|---|
| BA7 — Orchestration layer (thin framework + Ollama Projectionist/Archivist) | Next |
| BA8 — Self-migration audit (north_stars, patterns review) | After BA7 |
| BA9 — Prime Directives compliance verification across all agent contracts | After BA8 |
| Stage 1 — pgvector semantic search on frames | Future |
| Stage 2 — Inner monologue / Phase 2 belief processing | Future |
| Stage 4 — Full agent army, Tasker pattern, dedicated hardware | Future |
| Quartermaster — App permission layer, tier management | Future |
| Frontend — Direct Supabase connection (removes brain.sh dependency for writes) | Future |

---

*This document reflects system state at BA6 close (2026-04-11).*
*Maintained at: `docs/helm-system-design-ba6.md`*
*Next update: BA7 close.*
