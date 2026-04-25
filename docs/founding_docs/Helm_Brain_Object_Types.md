# Helm Brain Object Types — Roadmap

| | |
|---|---|
| **Status** | 🟢 Canonical reference |
| **Authored** | 2026-04-24, surfaced during V2 spec architecture review |
| **Purpose** | Catalog every type of object Helm can store in his brain, what each one is for, when each one gets written, and how each one shapes Helm's behavior. The reference for "what kind of mind are we building?" |
| **Audience** | Anyone designing a brain table, write helper, agent prompt, or scheduled pass. Required reading before T2.x design work and required reading before any Stage 2 cognitive expansion. |
| **Related** | `docs/founding_docs/Helm_The_Ambient_Turn.md` (vision), `docs/founding_docs/Helm_Roadmap.md` (sequencing), `docs/stage1/Post_T1_Findings.md` (queue) |

---

## Premise

Helm's brain is not a memory store. It is a **mind** — and minds have many different kinds of objects in them, each with its own epistemic status, write triggers, and use cases. A belief is not a hypothesis. A goal is not a curiosity. A surprise is not a frame. Conflating them under a single "memory" abstraction was the v1 mistake the V2 spec already partially corrects (with the expanded `MemoryType` enum in T0.B1).

This document catalogs every object type Helm should eventually have, with a clear delineation between:

- **Tier 1 (in T1):** types that exist or are spec'd in V2 today
- **Tier 2 (early Stage 2 / first batch post-T1):** types that materially deepen Helm's coherence and are cheap-ish to add
- **Tier 3 (later Stage 2+):** types that require ambient/scheduled infrastructure (T2/T3 work) to be meaningful

The goal is not to add everything. The goal is to make sure the **memory module abstraction (T0.B1)** is designed so that adding any of these later is *additive*, not surgical.

---

## Tier 1 — Existing or spec'd in V2 (T1 scope)

These are the brain types V2 either ships with or formally specs.

### `helm_memory`

The canonical event log. Behavioral entries (significant decisions, framings, observations) and scratchpad entries (active session working memory). Every other table is downstream of or derived from this.

- **Schema:** id, project, agent, memory_type, content, sync_ready, synced_to_core, session_date, created_at
- **Write triggers:** behavioral entry per significant decision, scratchpad entry per session moment, frame entries via Routine 4
- **Read patterns:** session-start delta query, category-scoped reads, full-history forensics
- **Owned by:** `helm.memory` module (T0.B1)
- **V2 work:** T0.B1 (module), T0.B6 (read client), expanded `MemoryType` enum

### `helm_memory_index`

Categorical structure — the table of contents Helm reads first at session start to know what categories of knowledge exist.

- **Schema:** id, project, agent, category, summary, entry_count, date_range_start, date_range_end, last_updated
- **Write triggers:** new category creation (per Routine 0 rules), volume-split, category retirement
- **Read patterns:** session start
- **V2 work:** existing seed categories (architecture, environment, decisions, people, projects, patterns, north_stars)

### `helm_personality`

Helm's identity, self-model, voice. The thing that makes Helm Helm across surfaces and across model swaps.

- **Schema:** sketch only — needs design work in T2.x
- **Write triggers:** rare, deliberate. Founding-document level changes only.
- **Read patterns:** loaded into every Prime prompt
- **Open question:** is this one row or many? Versioned? Signed by Maxwell?

### `helm_beliefs` + `helm_belief_history`

What Helm holds as committed positions about Maxwell, the world, Helm itself. Beliefs have *observation history* — the trail of evidence that justified the belief.

- **Schema:** id, project, agent, belief_text, confidence, formed_at, last_reinforced; history table tracks each observation that touched the belief
- **Write triggers:** belief formation (Routine 4), reinforcement on supporting evidence, weakening on counter-evidence
- **Read patterns:** Prime prompt context, Contemplator pass review
- **V2 work:** T2.5 (history table)

### `helm_frames`

Framed observations — the moments where Helm has named a pattern, given it shape. Distinct from raw memory entries (which are events) or beliefs (which are committed positions). A frame is "I see what's happening here, and here's the shape I'd give it."

- **Schema:** id, project, agent, frame_text, source_entries (FK array to helm_memory), formed_at
- **Write triggers:** Routine 4, Contemplator deep pass
- **Read patterns:** signals derivation, conversation context

### `helm_signals`

Derived view — the at-a-glance summary of what's currently active in Helm's awareness. Dual-write target from frames + patterns + open beliefs. UI surface for "what's Helm thinking about?"

- **Schema:** id, project, agent, signal_text, signal_kind, source_table, source_id, surfaced_at
- **Write triggers:** dual-write hook in `memory.write` (T2.6), reconciliation job (Stage 2)
- **Read patterns:** UI signal feed, Prime prompt summary
- **V2 work:** T2.4 (table), T2.6 (dual-write hook)

### `helm_entities`

People, projects, concepts, places, organizations Helm knows about by name.

- **Current schema:** name, count (shallow — V2 work plan deepens this in Tier 2 below)
- **Write triggers:** entity mention extraction during Routine 4
- **Read patterns:** entity-scoped memory lookup, Prime prompt context for "who/what is X?"
- **V2 work:** T2.7 (RPC `get_entities_with_counts`)
- **Note:** the *table* is in T1, but the *model* is shallow. Tier 2 below proposes deepening.

### `helm_messages`

Chat history — the literal conversation transcript. Distinct from memory (which is what Helm *extracted* from the conversation). Every message in, every message out.

- **Schema:** id, project, session_id, role (user/helm), content, created_at, correlation_id
- **Write triggers:** every `/invoke` request and response
- **Read patterns:** session reconstruction, conversation context window

---

## Tier 2 — First batch post-T1 (Post_T1_Findings.md Finding #001)

These three are explicitly queued as the **first work after T1 closes**. They materially deepen the hello-world experience and are cheap to add given the T0.B1 abstraction.

### `helm_curiosities` (NEW)

A queue of open questions Helm has formed but not resolved. Without curiosity, Helm only responds — he never drives. Curiosity is the substrate that makes T2 (scheduled passes) actually *do* something.

- **Schema sketch:**
  ```sql
  CREATE TABLE helm_curiosities (
    id UUID PRIMARY KEY,
    project TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT 'helm',
    question TEXT NOT NULL,
    formed_from UUID REFERENCES helm_memory(id),  -- the entry that sparked it
    priority TEXT CHECK (priority IN ('low', 'medium', 'high')),
    status TEXT CHECK (status IN ('open', 'investigating', 'resolved', 'abandoned')),
    resolution TEXT,
    formed_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
  );
  ```
- **Write triggers:** Routine 4 ("I noticed this but didn't have context — flag it"), explicit Maxwell prompt ("be curious about X")
- **Read patterns:** Prime prompt ("Helm currently wondering about: ..."), T2 scheduled pass picks one to investigate, UI "Helm's open questions" widget
- **Examples from this very session:** "What does Maxwell mean by 'Feats'?" "Why did Helm flip the deployment recommendation twice in one session?" "Is Pro Max weekly budget closer to 5M or 50M tokens — should the default change?"

### `helm_promises` (NEW)

Things Helm explicitly committed to do, with deadlines or check-back conditions. Without a place to live, "I'll watch for over-engineering" is just words. With one, Helm can return to it.

- **Schema sketch:**
  ```sql
  CREATE TABLE helm_promises (
    id UUID PRIMARY KEY,
    project TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT 'helm',
    promise_text TEXT NOT NULL,
    made_at TIMESTAMPTZ DEFAULT NOW(),
    due_at TIMESTAMPTZ,
    check_back_condition TEXT,  -- e.g. "next time Maxwell mentions Stage 2"
    status TEXT CHECK (status IN ('open', 'fulfilled', 'broken', 'released')),
    fulfillment_entry_id UUID REFERENCES helm_memory(id)
  );
  ```
- **Write triggers:** Helm utters "I will...", "I'll watch for...", "Next time you...". Routine 4 captures it.
- **Read patterns:** Prime prompt ("Open promises: ..."), session-end check ("did I fulfill any promises?"), T3 ambient surfaces them at relevant moments
- **Why important:** without this, Helm is full of intentions Maxwell has to remember on Helm's behalf. Trust corrodes.

### `helm_entities` deepened (EXTEND existing)

Current schema is `name, count`. That's not an entity — that's a tag with a counter. A real entity model:

- **Schema additions:**
  ```sql
  ALTER TABLE helm_entities ADD COLUMN entity_type TEXT CHECK (
    entity_type IN ('person', 'project', 'concept', 'place', 'organization', 'tool', 'event')
  );
  ALTER TABLE helm_entities ADD COLUMN aliases TEXT[];
  ALTER TABLE helm_entities ADD COLUMN attributes JSONB;
  ALTER TABLE helm_entities ADD COLUMN first_mentioned_at TIMESTAMPTZ;
  ALTER TABLE helm_entities ADD COLUMN last_mentioned_at TIMESTAMPTZ;
  ALTER TABLE helm_entities ADD COLUMN salience_decay FLOAT DEFAULT 1.0;

  CREATE TABLE helm_entity_relationships (
    from_entity UUID REFERENCES helm_entities(id),
    to_entity UUID REFERENCES helm_entities(id),
    relationship TEXT,  -- 'works_with', 'part_of', 'opposite_of', 'similar_to'
    formed_at TIMESTAMPTZ DEFAULT NOW(),
    confidence FLOAT
  );
  ```
- **Why important:** Helm needs to distinguish "your friend Sarah" (person) from "the Hammerfall project" (project) from "the concept of compounding" (concept). They get different prompt context, different decay rates, different surfacing logic.

---

## Tier 3 — Later Stage 2+ (require T2/T3 infrastructure to be meaningful)

These types are valuable but their value depends on Helm being *active* (scheduled passes, ambient operation). Adding them at T1 means writing tables that nobody reads until later. Better to wait.

### `helm_goals`

What Helm thinks Maxwell is trying to accomplish — short, medium, long term. Distinct from beliefs. Lets Helm orient: "Is this conversation in service of Stage 1 close, or unrelated?"

- **Why Tier 3:** goals need to be *acted on* — Helm noticing "this conversation isn't serving the goal" is only useful if Helm can do something about it. T3 ambient surfaces it; T1 just talks.

### `helm_hypotheses`

Helm's working theories — probabilistic, testable. Different epistemic status from beliefs (which are committed). "I think Maxwell prefers X, but I'm not sure" is a hypothesis. Watching the next 5 conversations would test it.

- **Why Tier 3:** hypotheses need *testing*, which means scheduled passes that compare prediction to outcome. T2 work.

### `helm_anticipations`

What Helm expects to happen next based on patterns. The substrate for `helm_surprises`.

- **Why Tier 3:** anticipations only matter if you compare them to reality. That's an ambient pass.

### `helm_surprises`

Moments where reality diverged from anticipation. High-signal for learning.

- **Why Tier 3:** depends on `helm_anticipations`.

### `helm_tensions`

Contradictions Helm is wrestling with. "Maxwell wants speed AND quality" — naming the tension is half the work.

- **Why Tier 3:** tensions need ongoing reflection (Contemplator passes scheduled), which is T2 work.

### `helm_watchlist`

Things Helm is monitoring for state change. "Did the Render budget hold this month?" "Has Maxwell mentioned Stage 2 yet?"

- **Why Tier 3:** the whole point is automated checks — T2 scheduled work.

### `helm_affinities`

Things Maxwell likes/dislikes. Subtler than beliefs — texture, not commitments. "Maxwell prefers tables to bullet lists in spec docs."

- **Why Tier 3:** valuable but T1 conversation can do without. Easier to add when patterns are visible across many sessions.

### `helm_routines`

Recurring patterns in Maxwell's day/week. Substrate for ambient anticipation.

- **Why Tier 3:** by definition needs many sessions to detect.

---

## Implications for the T0.B1 memory module abstraction

**The memory module shipped in T0.B1 must NOT be hardcoded around the Tier 1 types.** Specifically:

1. **`MemoryType` enum should be additive.** Adding `CURIOSITY`, `PROMISE`, `HYPOTHESIS`, `ANTICIPATION`, `SURPRISE`, `TENSION` later should be a one-line enum extension — not a refactor of every write helper.
2. **Per-type write helpers should follow a consistent pattern.** `write_behavioral`, `write_curiosity`, `write_promise` all take similar args, return similar types, emit similar events. Generic via a `write(type, content, **kwargs)` core.
3. **Per-type read helpers should be discoverable.** `read_recent(type=...)`, `read_open(type=...)` — no per-type custom query API.
4. **Outbox + dual-write hook patterns should work for any type.** T2.6's signals dual-write is the reference; future types follow the same shape.
5. **Schema migrations for new types should be a single migration each.** Don't bundle them.

**Concretely for T0.B1:** the memory module's public surface should be wide enough that adding `helm_curiosities` later is a 50-line PR (migration + enum line + write helper + read helper + a few tests), not a 500-line PR.

This is the load-bearing constraint. Get T0.B1's abstraction right, and the entire roadmap above is additive over years. Get it wrong, and every new brain type is a fight.

---

## Maintenance

This document is **founding-doc quality** — referenced for years. Update it when:

- A new brain type is identified (add to appropriate tier)
- A type moves between tiers (with rationale and date)
- A type is implemented (move from "spec'd" to "shipped" with link to migration PR)
- The T0.B1 abstraction proves insufficient for some new type (capture the failure mode + fix in the constraints section above)

The Post-T1 Findings doc (`docs/stage1/Post_T1_Findings.md`) tracks the *operational queue* — this doc tracks the *architectural reference*.
