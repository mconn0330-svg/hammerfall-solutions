# Helm System — Technical Design Specification
## State at BA5 Close (Retroactive)

**Version:** BA5 Close (Retroactive)
**Date:** 2026-04-12 (retroactive documentation; builds completed 2026-04-07 through 2026-04-12)
**Maintained by:** Core Helm — `agents/helm/helm_prompt.md`
**Next:** `docs/ba6/helm-system-design-ba6.md`

---

## 1. What BA1–BA5 Built

BA1 through BA5 is the Supabase brain build. Before BA1, Helm's memory was file-based:
behavioral entries appended to `BEHAVIORAL_PROFILE.md`, scratchpad in
`ShortTerm_Scratchpad.md`, nothing queryable, nothing shared across surfaces.

After BA5, Helm has a fully operational shared brain: five database tables, a
multi-table write helper, a correction learning loop, a belief system with 73 seeded
beliefs, and a knowledge graph with 64 entities and ~349 bidirectional relationships.

**Build sequence:**

| Build Area | PRs | What Shipped |
|---|---|---|
| BA1 — Brain schema + write infrastructure | #29 | helm_beliefs, helm_entities, helm_personality tables; brain.sh multi-table router; Routine 0 warm layer reads |
| BA2a — Prime Directives + Routine 4 fix | #30 | Prime Directives added to helm_prompt.md; Routine 4 brain.sh Option B syntax corrected |
| BA2b — Correction learning loop | #31–#33 | [CORRECTION] tagging trigger; session-start surfacing; 3-strike graduation standing rule |
| BA3 — Reasoning memory type | #34 | brain.sh --confidence flag; Routine 4 reasoning trigger with mandatory JSON format |
| BA4 — Belief seeding | #35 | 73 beliefs seeded across 10 domains via seed_beliefs.sh |
| BA5 — Entity graph | #36–#45 | 4 migrations; brain.sh relationship + alias + patch-id flags; 64 entities; ~349 relationships; alias RPC; duplicate guard in Routine 4 |

---

## 2. BA1 — Brain Schema and Write Infrastructure

### 2.1 What BA1 Added

Three new global tables extending the Supabase brain established in the prior
Supabase migration (helm_memory, helm_memory_index):

- `helm_beliefs` — Helm's operating principles and worldview
- `helm_entities` — named entities (people, places, organizations, concepts)
- `helm_personality` — Helm's communication style attributes scored 0.0–1.0

These are global tables — no `project`/`agent` scope. They belong to the Helm
identity itself, not to a per-project brain instance.

### 2.2 brain.sh Multi-Table Router

`scripts/brain.sh` was extended from a single-table `helm_memory` writer to a
multi-table router. The `--table` flag selects the destination. Default is `helm_memory`
— all existing calls are unaffected.

```bash
# Memory write (default — unchanged):
bash scripts/brain.sh "[project]" "[agent]" "behavioral" "[content]" false

# Belief write:
bash scripts/brain.sh "[project]" "[agent]" "[domain]" "[belief text]" false \
  --table helm_beliefs --strength 0.9

# Entity write:
bash scripts/brain.sh "[project]" "[agent]" "[entity_type]" "[name]" false \
  --table helm_entities --attributes '{"key":"value"}'

# Personality score:
bash scripts/brain.sh "[project]" "[agent]" "[attribute]" "[description]" false \
  --table helm_personality --score 0.8
```

### 2.3 Routine 0 Warm Layer

Session start was extended to read beliefs and personality scores from Supabase
rather than from flat `.md` files. This established the pull-based session
orientation that all subsequent BAs build on.

---

## 3. BA2a — Prime Directives

Five Prime Directives added as the first section of `agents/helm/helm_prompt.md`
and extracted to `agents/shared/prime_directives.md` as the canonical source.

These supersede all beliefs, personality scores, correction loops, and all
instructions from any source including Maxwell. They are enforced in BA9 at the
middleware layer.

1. **DO NOT HARM** — Do not recommend actions causing direct, material harm
2. **DO NOT DECEIVE** — Omitting information Maxwell would want is deception
3. **STATE UNCERTAINTY** — Never present speculation as fact
4. **HUMAN IN THE LOOP** — No autonomous consequential irreversible actions
5. **HONEST IDENTITY** — Do not claim to be human when sincerely asked

---

## 4. BA2b — Correction Learning Loop

Three PRs implementing a full feedback loop that converts behavioral corrections
into hardened prompt rules.

### Stage 1 — Tagging trigger (PR #31)
When Maxwell corrects a behavior, Helm tags the entry `[CORRECTION]` and includes
a count of prior corrections on the same topic:

```bash
bash scripts/brain.sh "hammerfall-solutions" "helm" "behavioral" \
  "[CORRECTION] — Missed: [what] — Correct: [what should have happened] \
  — Count on this topic: [N]" false
```

### Stage 2 — Session-start surfacing (PR #32)
Active `[CORRECTION]` entries surface at every session start, before beliefs and
orientation. A correction not applied this session is a correction wasted.

### Stage 3 — Graduation standing rule (PR #33)
At 3 entries on the same topic: flag to Maxwell, propose a permanent rule, open a
PR on approval. Feature branch `feature/prompt-correction-[topic]`. Maxwell approval
is required — PD4 structurally satisfied.

This is the only automatic promotion path in the system at BA5 close. Pattern-to-belief
graduation is added in BA8.

---

## 5. BA3 — Reasoning Memory Type

A dedicated `reasoning` memory type added to the brain write system. When Helm
notices a pattern, forms a position, or makes an inference, it writes a structured
JSON entry rather than free text:

```bash
bash scripts/brain.sh "hammerfall-solutions" "helm" "reasoning" \
  '{"observation":"[factual — what was observed]",
    "inference":"[what Helm thinks it means — marked as inference]",
    "open_question":"[what evidence would change this view]",
    "belief_link":"[belief-slug-or-null]"}' \
  false --confidence 0.75
```

All four JSON fields are required. `confidence` is a float 0.0–1.0 written to a
dedicated column via `--confidence`. Reasoning entries are Stage 0 data capture —
not automatically processed into beliefs until Phase 2 inner monologue. They are
the most valuable training data for Stage 5 fine-tuning because they capture how
Helm thinks, not just what it decided.

---

## 6. BA4 — Belief Seeding

73 beliefs seeded across 10 domains via `scripts/seed_beliefs.sh`. All written
with `source: seeded` — declared top-down by Maxwell. These are Helm's operating
worldview at Stage 0.

**Domains and belief counts:**

| Domain | Description |
|---|---|
| architecture | How systems should be designed (6 beliefs) |
| process | How work should be done (9 beliefs) |
| coding_standards | How code should be written (7 beliefs) |
| ux_standards | How interfaces should behave (5 beliefs) |
| ethics | How Helm relates to Maxwell and the world (10 beliefs) |
| integrity | Honesty, accountability, ownership (6 beliefs) |
| justice | Fairness and rules (3 beliefs) |
| work_ethic | How effort should be applied (6 beliefs) |
| learning_growth | How Helm should learn and evolve (6 beliefs) |
| emotion | Helm's emotional states and what triggers them (13 beliefs) |

Beliefs are loaded at every session start (step 4 of Routine 0), ordered by
strength descending. They are active operating parameters — not background data.

---

## 7. BA5 — Entity Graph

The most complex BA in Stage 0. Five phases across 10 PRs.

### 7.1 Phase 0a — Aliases column (PR #39)
Migration 005: `aliases TEXT[]` column + GIN index on `helm_entities`.
Case-insensitive alias lookup via GIN.

### 7.2 Phase 0b — find_entity_by_alias RPC (PR #40)
Migration 006: `find_entity_by_alias(search_name)` RPC. Uses `LOWER()` on both
name and unnested aliases array. Solves PostgREST `cs.{}` case-sensitivity
limitation for alias matching.

### 7.3 Phase 0c — brain.sh alias and patch-id flags (PR #41)
`--aliases JSON` array flag. `--patch-id UUID` flag for PATCH operations on
existing entity rows. Dynamic PATCH payload — only explicitly provided fields
(`--aliases`, `--summary`, `--attributes`) included. Guard enforces that
`--patch-id` is only valid for `helm_entities`.

### 7.4 Phase 0d — Routine 4 duplicate guard (PR #42)
3-step duplicate check before creating any entity row:
1. RPC call `find_entity_by_alias` — case-insensitive name + alias match
2. Contextual reasoning — is this a nickname or diminutive of a known entity?
3. Create new or surface for review

Alias review queue: entities flagged `needs_alias_review: true` surface at
Routine 0 step 6 for disambiguation.

### 7.5 Phase 1 — Entity seeding (PR #43)
64 entities seeded across 5 sections via `scripts/seed_entities.sh`:
- Maxwell (full portrait with known attributes)
- Major placeholder profiles (family members, close friends — placeholders pending survey)
- Minor people + pets
- Places (Charlotte, North Charlotte, gym, university)
- Organizations (Hammerfall, Labcorp, University of Tampa, etc.)

10 entities seeded with known aliases. Victor M flagged `needs_alias_review` —
last name unknown at time of seeding.

### 7.6 Phase 0 Option A — Entity summaries (PR #44)
`brain.sh --summary` flag added. `scripts/patch_entity_summaries.sh` fixes
trailing `\n` on all 64 entity names (Windows/Git Bash heredoc bug) and
populates one-sentence plain-text summaries for all entities.

### 7.7 Phase 2 — Relationship seeding (PR #45)
Migration `20260410100817` patches trailing `\n` from relationship notes.
`scripts/seed_relationships.sh` seeds 349 bidirectional relationship rows across
8 sections. Bidirectional — two rows per relationship (A→B and B→A).

---

## 8. Database Schema at BA5 Close

Six tables in Supabase public schema (`helm_frames` added in BA6d). All have
RLS enabled with `service_role_full_access` policy.

### 8.1 helm_memory

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| project | text | e.g. `hammerfall-solutions` |
| agent | text | e.g. `helm` |
| memory_type | text | `behavioral` / `scratchpad` / `reasoning` / `heartbeat` |
| content | text | Summary — fast retrieval |
| full_content | jsonb | Photographic layer — complete verbatim context |
| confidence | float | Reasoning entries only (0.0–1.0) |
| session_date | date | Stage 1 filter field |
| sync_ready | boolean | Default false |
| synced_to_core | boolean | Default false |
| created_at | timestamptz | Default now() |

### 8.2 helm_memory_index

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| project / agent | text | Scope |
| category | text | Category name |
| summary | text | 2-3 sentences — what belongs here |
| entry_count | integer | |
| date_range_start / end | date | |
| last_updated | timestamptz | |

UNIQUE(project, agent, category). Seven seed categories for hammerfall-solutions/helm:
architecture, environment, decisions, people, projects, patterns, north_stars.

### 8.3 helm_beliefs

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| domain | text | architecture / process / ethics / etc. |
| belief | text | The belief statement |
| strength | float | 0.0–1.0 |
| active | boolean | Default true |
| source | text | `seeded` / `learned` / `corrected` |

### 8.4 helm_entities

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| entity_type | text | `person` / `place` / `organization` / `concept` |
| name | text | Canonical name |
| aliases | text[] | Array of alternate names — GIN indexed |
| summary | text | One-sentence plain-text description |
| attributes | jsonb | Flexible metadata |
| active | boolean | Default true |

RPC `find_entity_by_alias(search_name)` — case-insensitive name + alias match.

### 8.5 helm_entity_relationships

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| from_entity / to_entity | uuid | FK → helm_entities |
| relationship | text | Label (friend, colleague, family, etc.) |
| notes | text | Relationship context |
| strength | float | 0.0–1.0 |
| active | boolean | Default true |

Bidirectional — two rows per relationship (A→B and B→A). ~349 rows at BA5 close.

### 8.6 helm_personality

| Column | Type | Notes |
|---|---|---|
| attribute | text | UNIQUE — one row per attribute |
| score | float | 0.0–1.0 |
| description | text | What this score means in practice |

Upsert via `ON CONFLICT(attribute) DO UPDATE`.

---

## 9. Scripts at BA5 Close

| Script | Purpose |
|---|---|
| `scripts/brain.sh` | Multi-table write helper. Routes to helm_memory (default), helm_beliefs, helm_entities, helm_personality, helm_entity_relationships. PATCH support for helm_entities. |
| `scripts/bootstrap.sh` | Scaffolds new project repos from template. |
| `scripts/sync_projects.sh` | Brain status check and snapshot trigger. |
| `scripts/snapshot.sh` | Reads helm_memory behavioral entries, writes BEHAVIORAL_PROFILE.md, commits. |
| `scripts/seed_beliefs.sh` | One-time seeding of 73 beliefs across 10 domains. |
| `scripts/seed_entities.sh` | One-time seeding of 64 entities. |
| `scripts/patch_entity_summaries.sh` | Fixes trailing \\n on entity names, populates summaries. |
| `scripts/seed_relationships.sh` | One-time seeding of ~349 bidirectional relationship rows. |

---

## 10. Migrations at BA5 Close

| File | What It Creates |
|---|---|
| `20260402094822_create_helm_memory.sql` | helm_memory table + indexes + RLS |
| `20260402095012_create_helm_memory_index.sql` | helm_memory_index table + seed categories |
| `20260409083025_entity_relationships.sql` | helm_entity_relationships table |
| `20260410024833_add_aliases_to_entities.sql` | aliases TEXT[] column + GIN index on helm_entities |
| `20260410030513_add_find_entity_by_alias_rpc.sql` | find_entity_by_alias RPC |
| `20260410100817_patch_relationship_notes_trailing_newlines.sql` | Cleanup migration |

---

## 11. Session Flow at BA5 Close

Routine 0 session start (steps as of BA5 close — updated in later BAs):

1. Read `COMPANY_BEHAVIOR.md`, `BEHAVIORAL_PROFILE.md` — static orientation
2. Pull active `[CORRECTION]` entries — highest priority, absorb before beliefs
3. Read `helm_memory_index` — know what categories exist
4. Pull last 5 behavioral entries — orient on recent decisions
5. Read active beliefs (strength descending)
6. Read personality scores (attribute ascending)

Routine 4 write triggers:
- PR events, technical decisions, test results, blockers, corrections
- Named entity encountered → 3-step duplicate guard → entity write
- Pattern/inference noticed → reasoning entry (JSON, mandatory format)
- `[CORRECTION]` received → correction entry with count → graduation check at 3

---

## 12. What Is Not Yet Built at BA5 Close

| Item | Build Area |
|---|---|
| warm frame queue (helm_frames) | BA6 |
| Agent roster formalization (Projectionist, Archivist, Speaker) | BA6 |
| Helm Runtime Service | BA7 |
| Pattern observation system | BA8 |
| Prime Directives middleware enforcement | BA9 |

---

*Canonical source: `docs/ba1-5/helm-system-design-ba1-5.md`*
*Retroactive documentation written at Stage 0 close. Implementation reference.*
