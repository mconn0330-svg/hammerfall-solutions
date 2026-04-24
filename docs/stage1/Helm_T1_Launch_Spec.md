# Helm T1 Launch — Consolidated Build Specification

| | |
|---|---|
| **Status** | 🟡 Active — Lane C closing, T1 Launch work begins |
| **Purpose** | Complete all backend prep, UI gap resolution, and integration work required to achieve Stage 1 T1 on-demand presence at production quality. |
| **Estimated PRs** | 15-18 |
| **Exit criteria** | A user opens the UI, talks to Helm, sees live agent activity, and experiences a coherent identity — all on real data, no mocks. |

---

## What This Spec Covers

This is everything between "Lane C closes" and "Stage 1 exit outcomes achieved." It consolidates what was previously tracked as Lane A (backend integration prep) and Lane B (UI build) into a single sequenced plan.

Three phases:

1. **Phase 1 — Freestanding work** (can start now, no blockers)
2. **Phase 2 — Backend build** (requires Lane C closed)
3. **Phase 3 — Integration + launch validation** (requires Phase 2 complete)

---

## Progress Tracker

### Phase 1 — Freestanding (start now)

| Task | Description | Type | Status |
|---|---|---|---|
| T1.1 | Remove Speaker from mockData.js | UI | 🔵 Ready |
| T1.2 | Update mock IDs to UUIDs | UI | 🔵 Ready |
| T1.3 | Hardcode personality translations in widget | UI | 🔵 Ready |
| T1.4 | Date formatting utility | UI | 🔵 Ready |
| T1.5 | Glass morphism + visual polish pass | UI | 🔵 Ready |
| T1.6 | Commit Supabase anon key to repo (`.env`) | Helm IDE | 🟡 Key obtained |
| T1.7 | UI Interaction Spec document (three layers) | Architect | 🔵 Ready |

### Phase 2 — Backend Build (blocked on Lane C close)

| Task | Description | Type | Status |
|---|---|---|---|
| T2.1 | Supabase prompt storage | Helm IDE build | 🔵 Queued — FIRST |
| T2.2 | Schema reference doc (Widget Data Map output) | Helm IDE | 🔵 Queued |
| T2.3 | Contemplator→Archivist async handoff | Helm IDE build | 🔵 Queued |
| T2.4 | SSE endpoint + UI directive support | Helm IDE build | 🔵 Queued |
| T2.5 | Add slug column to helm_beliefs | Helm IDE build | 🔵 Queued |
| T2.6 | Belief observation history | Helm IDE build | 🔵 Queued |
| T2.7 | RPC function get_signals() | Helm IDE build | 🔵 Queued |
| T2.8 | RPC function get_entities_with_counts() | Helm IDE build | 🔵 Queued |

### Phase 3 — Integration + Launch Validation (blocked on Phase 2)

> **⛔ DO NOT START Phase 3 until explicitly cleared by Maxwell.**

| Task | Description | Type | Status |
|---|---|---|---|
| T3.1 | JSON + fallback response parser | UI | 🔴 Blocked on T2.4 |
| T3.2 | executeDirective() handler | UI | 🔴 Blocked on T2.4 |
| T3.3 | Connect UI to real Supabase | UI | 🔴 Blocked on T1.6 + T2.5-T2.8 |
| T3.4 | Connect UI to real runtime | UI | 🔴 Blocked on Lane C + T2.4 |
| T3.5 | T1 Launch validation | Test | 🔴 Blocked on T3.1-T3.4 |

### Previously Completed

| Task | Description | Status |
|---|---|---|
| RLS policies on all 8 brain tables | ✅ Done |
| Supabase Realtime on all 7 tables | ✅ Done |
| Console drawer + chat tab (PR #81) | ✅ Done |
| Activity/System tabs + split view (PR #81) | ✅ Done |
| Docked widgets + minimize pills (PR #81) | ✅ Done |
| Position settings + full-screen + slash commands | ✅ Done |
| Widget viewport clamping + quadrant stacking | ✅ Done |

---

## Phase 1 — Freestanding Tasks

These tasks have zero backend dependency. Start immediately. Each is a standalone PR.

---

### T1.1 — Remove Speaker from mockData.js

**What:** The `AGENT_STATUS`, `ACTIVITY`, and `LOGS.system` arrays in `helm-ui/src/data/mockData.js` still contain Speaker entries. Speaker was killed in PR #78. The mock data must reflect the current four-agent cognitive architecture: Helm Prime, Projectionist, Archivist, Contemplator.

**File:** `helm-ui/src/data/mockData.js`

**Changes:**

1. **`AGENT_STATUS` array** — Find and remove the entire Speaker object. Four agent entries should remain: Helm Prime (Anthropic, claude-opus-4-6), Projectionist (Ollama, qwen3:4b), Archivist (Ollama, qwen3:14b), Contemplator (Ollama, qwen3:14b).

2. **`ACTIVITY` array** — Find any activity entries where `agent` is `"Speaker"` or the `message` references Speaker routing. Remove these entries or update them to reference `"Helm Prime"`.

3. **`LOGS` object** — Check `session`, `contemplator`, and `system` arrays. Update "All 5 agents reachable" to "All 4 agents reachable." Update any `routing: "SPEAKER"` or `routing: "LOCAL"` to `routing: "HELM_PRIME"`.

**Verification:** Run the UI (`cd helm-ui && npm run dev`). Open Agent Status widget — four agents. Open Console Activity tab — no Speaker. Open Console System tab — no "5 agents" references.

**Deliverable:** One PR — mockData.js cleanup only.

---

### T1.2 — Update Mock IDs to UUIDs

**What:** Mock data uses short IDs (`"b1"`, `"e1"`, `"s1"`, `"mem1"`). Supabase uses UUIDs (36-character strings like `"8f3a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"`). If UI components break on long IDs (truncation, column overflow, key collisions), we need to find out now.

**File:** `helm-ui/src/data/mockData.js`

**Changes:** Replace every `id` field across all mock arrays with properly formatted UUIDs. Use deterministic fake UUIDs for readability (e.g., `"00000000-0000-4000-8000-000000000001"` for belief 1).

**Affected exports:** `PERSONALITY`, `BELIEFS`, `ENTITIES`, `SIGNALS`, `AGENT_STATUS`, `MEMORY`, `ACTIVITY` — every export with an `id` field.

**What to watch for:** Any widget that displays IDs, uses IDs as React `key` props, or cross-references by ID. Verify nothing overflows or breaks.

**Deliverable:** One PR — mockData.js ID updates. Can combine with T1.1.

---

### T1.3 — Hardcode Personality Translations

**What:** The `PERSONALITY` mock includes a `translations` object mapping score ranges to human-readable descriptions (e.g., directness 0.0 = "Softens every point, frames diplomatically"). This does not exist in the `helm_personality` Supabase table and should not — translations are presentation logic, not brain content.

**File:** PersonalityWidget component (likely `helm-ui/src/widgets/PersonalityWidget.jsx`)

**Changes:**

1. Create a constant in the PersonalityWidget file with the full translations mapping per dimension. Copy the exact values from the current `PERSONALITY` mock data entries. Structure:

```javascript
const PERSONALITY_TRANSLATIONS = {
  directness: {
    0.0: "Softens every point, frames diplomatically",
    0.2: "Gentle framing, avoids bluntness",
    0.5: "Balanced — direct when it matters, diplomatic otherwise",
    0.8: "Says it straight, minimal cushioning",
    1.0: "Unvarnished, blunt, zero sugar-coating"
  },
  challenge_frequency: { /* ... */ },
  verbosity: { /* ... */ },
  formality: { /* ... */ },
  show_reasoning: { /* ... */ },
  sarcasm: { /* ... */ }
};
```

2. Add a lookup function that finds the nearest translation for the current score:

```javascript
function getTranslation(attribute, score) {
  const translations = PERSONALITY_TRANSLATIONS[attribute];
  if (!translations) return '';
  const keys = Object.keys(translations).map(Number).sort((a, b) => a - b);
  const nearest = keys.reduce((prev, curr) =>
    Math.abs(curr - score) < Math.abs(prev - score) ? curr : prev
  );
  return translations[nearest];
}
```

3. Remove `translations` from `PERSONALITY` entries in mockData.js.

**Verification:** Run the UI, open Personality widget. Each dimension shows a description matching its score. Moving sliders updates descriptions.

**Deliverable:** One PR — PersonalityWidget constant + mockData.js cleanup.

---

### T1.4 — Date Formatting Utility

**What:** Supabase returns ISO 8601 timestamps (`"2026-04-14T09:14:03.000Z"`). The UI uses clean strings (`"2026-04-14"`, `"09:14:00"`) in mocks. A shared utility prevents raw ISO strings from appearing when real data arrives.

**File to create:** `helm-ui/src/utils/formatDate.js`

**Implementation:**

```javascript
export function formatDate(isoString, format = 'datetime') {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '—';

  switch (format) {
    case 'date': return d.toLocaleDateString('en-CA');
    case 'time': return d.toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false
    });
    case 'datetime': return `${formatDate(isoString, 'date')} ${formatDate(isoString, 'time')}`;
    case 'relative': return getRelativeTime(d);
    default: return d.toISOString();
  }
}

function getRelativeTime(date) {
  const diffMs = Date.now() - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return `${Math.floor(diffMins / 1440)}d ago`;
}
```

**Where to apply:** Chat timestamps (`time`), Activity stream (`time`), System logs (`time`), Memory widget (`date`), Entities `first_seen` (`date`), Belief observations (`relative`), Contemplator logs (`datetime`).

**Verification:** Run the UI. No raw ISO strings visible anywhere.

**Deliverable:** One PR — utility file + widget updates.

---

### T1.5 — Glass Morphism + Visual Polish Pass

**What:** Comprehensive visual polish pass to achieve consistent neo-organic glass morphism across the entire Helm UI. The node and brain menu already express this style. The Console, docked widgets, and canvas widgets need to match.

**Design tokens — use these exact values for consistency:**

| Token | Value | Where |
|---|---|---|
| Background (app) | `#0a0e1a` to `#0d1420` | Root background. No pure black. |
| Panel surface | `rgba(10, 20, 40, 0.6)` to `rgba(15, 25, 50, 0.8)` | Console, widgets, all panels. Never opaque. |
| Blur | `backdrop-filter: blur(16px)` to `blur(24px)` | All panel surfaces. Node particles visible through panels. |
| Border | `0.5px solid rgba(80, 140, 220, 0.15)` | Panel edges. Thin, subtle, blue-tinted. Nothing above 1px. |
| Border hover | `border-color: rgba(80, 140, 220, 0.35)` | Subtle brightening on hover/focus. CSS transition for smooth fade. |
| Primary text | `#c8deff` | Body text, widget content. Soft blue-white. |
| Muted text | `rgba(120, 160, 210, 0.5)` | Secondary info, timestamps, user messages. |
| Label text | `#7ab4ff` with `letter-spacing: 1px` | Widget headers, tab labels, section titles. Accent blue. |
| Helm responses | `#a8c8ff` | Slightly brighter than primary. Helm's voice stands out. |
| User messages | `rgba(160, 200, 240, 0.5)` | Muted, receding. The user is the context, Helm is the foreground. |
| Status green | `#2aff8a` | Agent online, health ok. |
| Contemplator amber | `rgba(220, 160, 80, 0.8)` | Contemplation state, ◈ button. |
| Error red | `#ff4444` | Agent error, connection lost. |
| Interactive blue | `#3a7aff` | Buttons, links, active tab indicators. |
| Font | `'IBM Plex Mono', 'Space Mono', monospace` | All text. Monospace throughout. |
| Label size | `10-11px` | Widget headers, tab labels. |
| Body size | `12-13px` | Content text, chat messages. |
| Border radius | `6-8px` | Consistent across all panels and widgets. |
| Scrollbar | `scrollbar-width: thin; scrollbar-color: rgba(80, 140, 220, 0.2) transparent` | No bright scrollbars. |

**Components to audit:**

1. **Console drawer** — header bar, tab strip, chat pane background, split-view divider, input bar, Send button (`interactive blue at low opacity`), Contemplate button (◈, `amber at low opacity`), drawer resize handle (thin line, not a grab bar).

2. **Docked widget panels** — each widget in the Console right pane gets glass surface treatment. Widget headers use label style. Widget controls (minimize/expand/close) are `rgba(100, 150, 200, 0.3)`, brightening on hover.

3. **Canvas widgets** — widgets opened from the brain menu. Same glass treatment as docked versions. Same component, same styling, different container.

4. **Widget content** — belief scores, personality sliders, memory entries, entity cards follow the text color hierarchy. Interactive elements use interactive blue. Status indicators use green/amber/red.

5. **Console input bar** — `background: rgba(255, 255, 255, 0.04)` with `0.5px` border. Placeholder in muted text.

**What to avoid:**
- Opaque backgrounds on any panel
- Borders thicker than 1px
- Drop shadows (glass effect comes from blur + transparency, not elevation)
- Pure white text (always tinted blue)
- Inconsistent border radius
- Bright scrollbar tracks

**Verification:** Run the UI. The entire application should feel like one cohesive visual system. The node, brain menu, Console, and all widgets should look like they belong together.

**Deliverable:** One PR — CSS/style updates across Console and widget components.

---

### T1.6 — Commit Supabase Anon Key to Repo

**What:** Add the Supabase anon key to a committed `.env` file in `helm-ui/` so any device that clones the repo can connect to Supabase without manual setup.

**Why committed and not `.env.local`:** The anon key is designed to be public. It provides no privileged access — RLS policies control what it can read and write. Supabase's own documentation recommends putting the anon key in frontend code. The **service key** is the one that must never be committed (it bypasses RLS). Committing the anon key means any device, any clone, any deployment can reach Supabase immediately without per-machine configuration.

**Steps:**

1. Create `helm-ui/.env` (NOT `.env.local` — this file will be tracked by git):
```
VITE_SUPABASE_URL=https://zlcvrfmbtpxlhsqosdqf.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_9eE4T4FaYVLcYOg_1wok6g_W_nqCue8
```

2. Verify `.env.local` is in `helm-ui/.gitignore` (it should already be — `.env.local` is for per-machine overrides that should not be committed).

3. Verify `.env` is NOT in `.gitignore` (it should not be — this file is intentionally tracked).

4. Key source: Supabase Dashboard → Settings → API → `anon` (public) key. **NOT the service_role key.**

**Deliverable:** One PR — `helm-ui/.env` with Supabase URL and anon key. Verify `.gitignore` is correct.

---

### T1.7 — UI Interaction Spec Document

**What:** Write the spec document defining the full contract between UI and runtime. Three layers. This is the reference Helm IDE builds against for T2.4 and the UI team builds against for T3.1-T3.4.

**Owner:** Architect produces this. Not a Helm IDE build task.

**File:** `docs/stage1/ui-interaction-spec.md`

**Layer 1 — Request/Response Contract:**

Endpoints: `POST /invoke/helm_prime` (send message, receive response), `GET /health` (status), `GET /config/agents` (agent roster).

Request schema: `user_message` (string), `session_id` (UUID), `turn_number` (int), `context` (optional dict), `project` (optional string), `agent` (string).

Response: `{text: string, routing: string, ui_directives: array}` JSON. Plain text fallback.

Session management: UI generates UUID on first load, persists in localStorage, sends with every request.

Error handling: "Helm is unreachable" after three consecutive `/health` failures. Messages queue locally.

**Layer 2 — SSE Event Channel:**

Endpoint: `GET /events` — Server-Sent Events stream.

Event schema: `{type, agent, action, timestamp, payload}`

12 event types: `agent_invoked`, `agent_completed`, `agent_error`, `contemplator_pass_started`, `contemplator_pass_completed`, `frame_written`, `frame_migrated`, `belief_updated`, `curiosity_flag`, `personality_read`, `system_health`, `session_started`.

Node state mapping: `agent_invoked` (prime) → blue pulse, `contemplator_pass_started` → amber glow, `agent_completed` (prime) → idle, `agent_error` → red flash (3s decay).

**Layer 3 — UI Directives:**

7 actions: `open_widget`, `close_widget`, `minimize_widget`, `expand_widget`, `highlight_entry`, `open_split`, `close_split`.

7 widget identifiers: `agent_status`, `core_beliefs`, `personality`, `memory`, `entities`, `signals`, `logs`.

Directive decision lives in Prime's reasoning. Most responses have empty `ui_directives`.

**Deliverable:** One PR — `docs/stage1/ui-interaction-spec.md`.

---

## Phase 2 — Backend Build

Requires Lane C closed. These tasks modify `main.py`, `helm_prime.py`, Supabase schema, and `helm_prompt.md`.

---

### T2.1 — Supabase Prompt Storage

**Priority:** FIRST TASK when Lane C closes.

**What:** Move `helm_prompt.md` from volume-mounted file into Supabase. The prompt becomes brain content — versionable, deployment-agnostic, consistent with canonical brain rule.

**Table schema:**

```sql
CREATE TABLE helm_prompt (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL DEFAULT 'prime_system_prompt',
  content TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO helm_prompt (name, content)
VALUES ('prime_system_prompt', '<full helm_prompt.md content>');

ALTER TABLE helm_prompt ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_helm_prompt" ON helm_prompt
  FOR SELECT TO anon USING (true);
```

**Sync script:** `scripts/sync_prompt.sh` — reads `.md` file, pushes content to Supabase via curl PATCH.

**Handler update:** `_load_base_prompt()` reads from Supabase first, falls back to file. Non-fatal fallback (same pattern as personality loading).

**Post-merge (Maxwell):** Enable Realtime on `helm_prompt` in Dashboard.

**Deliverable:** One PR — migration + sync script + handler update.

---

### T2.2 — Schema Reference Doc

**What:** Widget Data Map output — documents every table, column, RPC, query pattern, and Realtime/RLS status. The reference for all integration work.

**File:** `docs/stage1/schema-reference.md`

**Write after T2.5-T2.8** so all schema changes are reflected.

**Deliverable:** One PR.

---

### T2.3 — Contemplator→Archivist Async Handoff

**What:** Wrap Archivist write calls in `asyncio.create_task()` so Contemplator returns immediately. Archivist writes run in the background. Errors logged, not propagated.

**Why now:** Prevents tech debt that surfaces during Stage 3 Thor deployment.

**Deliverable:** One PR — `main.py` orchestration change.

---

### T2.4 — SSE Endpoint + UI Directive Support

**What:** The largest task in this spec. Three parts:

**Part 1 — `GET /events` SSE endpoint in `main.py`:** Global event bus using `asyncio.Queue` per connected client. Add `sse-starlette` to requirements.txt. Add `emit_event()` calls at 12 locations in `main.py` (before/after each handler dispatch, in exception catches, at session start, on health checks).

**Part 2 — Response format change in `helm_prime.py`:** Output becomes `{text, routing, ui_directives}` JSON. Parser attempts to extract structured directives from model output, falls back to wrapping plain text.

**Part 3 — Directive vocabulary in `helm_prompt.md`:** New section teaching Prime about the 7 directive actions, 7 widget identifiers, when to emit directives, and the JSON response format.

**Deliverable:** One large PR or split into 2 (SSE endpoint + response format change).

---

### T2.5 — Add `slug` Column to `helm_beliefs`

**What:** UI cross-references beliefs by slug. Migration adds column + unique index. Backfill generates slugs from belief text (lowercase, hyphenated, first 5-6 words).

```sql
ALTER TABLE helm_beliefs ADD COLUMN slug TEXT;
CREATE UNIQUE INDEX idx_helm_beliefs_slug ON helm_beliefs(slug) WHERE slug IS NOT NULL;
```

**Deliverable:** One PR — migration + backfill.

---

### T2.6 — Belief Observation History

**What:** New `helm_belief_history` table tracking strength deltas. When Contemplator updates a belief, it reads current strength, writes a history row with previous/new/delta/summary, then updates the belief.

```sql
CREATE TABLE helm_belief_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  belief_id UUID REFERENCES helm_beliefs(id) ON DELETE CASCADE,
  previous_strength NUMERIC NOT NULL,
  new_strength NUMERIC NOT NULL,
  delta NUMERIC GENERATED ALWAYS AS (new_strength - previous_strength) STORED,
  summary TEXT NOT NULL,
  source TEXT DEFAULT 'contemplator',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Post-merge (Maxwell):** Enable RLS + Realtime on `helm_belief_history`.

**Deliverable:** One PR — migration + Contemplator write-path update.

---

### T2.7 — RPC Function `get_signals()`

**What:** Aggregate pattern entries from `helm_memory` into structured signal objects. Returns slug, statement, domain, first_seen, observation_count. Parsing depends on Routine 4's `Pattern — slug | statement | domain: X` format.

**Deliverable:** One PR — migration with RPC function.

---

### T2.8 — RPC Function `get_entities_with_counts()`

**What:** Return entities with relationship counts via LEFT JOIN against `helm_entity_relationships`.

**Deliverable:** One PR — migration with RPC function.

---

## Phase 3 — Integration + Launch Validation

> **⛔ DO NOT START Phase 3 until Maxwell explicitly clears each task.**
>
> **Wait for:** "T2.4 is merged — proceed with T3.1 and T3.2."
> **Wait for:** "T2.5-T2.8 are merged — proceed with T3.3."
> **Wait for:** "T3.3 is merged — proceed with T3.4."

---

### T3.1 — JSON + Fallback Response Parser

**Blocked on:** T2.4

**What:** Console ChatWidget switches from plain text to structured JSON. Parser attempts JSON parse, extracts `text` for display, `routing` for turn badge, queues `ui_directives`. Falls back to plain text if parse fails. **Fallback is critical** — plain text must always work.

**Deliverable:** One PR — parser + ChatWidget integration.

---

### T3.2 — `executeDirective()` Handler

**Blocked on:** T2.4

**What:** Execute UI directives from Helm's responses. Switch on action type, call widget manager methods (open, close, minimize, expand, highlight, openSplit, closeSplit). Unknown actions logged and ignored — forward-compatible.

**Deliverable:** One PR — directive handler + ChatWidget integration.

---

### T3.3 — Connect UI to Real Supabase

**Blocked on:** T1.6 + T2.5-T2.8

**What:** Replace ALL mock imports with Supabase queries. Create `helm-ui/src/lib/supabase.js` with client. Per-widget: Personality → `select *`, Beliefs → `select *` + history, Entities → `rpc('get_entities_with_counts')`, Signals → `rpc('get_signals')`, Memory → `select *` ordered, Agent Status/Logs/Activity → runtime endpoints + SSE.

Add Realtime subscriptions for live-updating widgets. Add loading states. Add error states.

**Deliverable:** Multiple PRs — per-widget or grouped.

---

### T3.4 — Connect UI to Real Runtime

**Blocked on:** Lane C + T2.4

**What:** Wire Chat to `POST /invoke/helm_prime`. Wire Activity/System tabs to `GET /events` SSE. Wire Helm node state to SSE events. Add connection status indicator (LIVE / DISCONNECTED / MOCKED).

**Deliverable:** One PR — chat + SSE + node state + connection indicator.

---

### T3.5 — T1 Launch Validation

**Blocked on:** T3.1-T3.4

**What:** End-to-end "Helm cares" test. Validation checklist:

- [ ] User talks to Helm, receives coherent response
- [ ] Response is structured JSON with text + routing
- [ ] Personality scores visibly affect responses (adjust directness, observe change)
- [ ] Contemplator curiosity flags surface at session start
- [ ] All four subsystems fire — visible in Activity tab as live SSE events
- [ ] Memory writes land in Supabase — visible in Memory widget
- [ ] Personality slider changes reflect in next response
- [ ] Belief history entries appear after strength changes
- [ ] Entity relationship counts are accurate
- [ ] Signals aggregate correctly
- [ ] SSE events stream live (not mocked)
- [ ] System tab shows real health checks and session IDs
- [ ] Node state matches activity (blue pulse, amber glow, idle)
- [ ] Slash commands work (/status, /beliefs, /contemplate)
- [ ] Split view: chat + activity simultaneously
- [ ] Connection indicator shows LIVE
- [ ] Runtime stopped → UI shows DISCONNECTED, queued messages send on reconnect
- [ ] Voice coherence: Helm in UI = Helm in IDE
- [ ] "Show me agent status" → Helm opens widget via directive

**Deliverable:** SITREP with pass/fail per item. Failures become fix tasks.

---

## Sequencing

```
NOW:
  T1.1-T1.5 — UI freestanding (no blocker)
  T1.6      — Commit anon key to repo (.env)
  T1.7      — UI Interaction Spec (Architect)

LANE C CLOSES:
  T2.1      — Supabase prompt storage (first)
  T2.2      — Schema reference doc
  T2.3      — Async handoff
  T2.4      — SSE + directives (largest, unblocks Phase 3)
  T2.5-T2.8 — Schema gaps + RPCs

PHASE 2 COMPLETE (Maxwell clears):
  T3.1-T3.2 — Parser + directives (after T2.4)
  T3.3      — Supabase integration (after T2.5-T2.8)
  T3.4      — Runtime integration (after T2.4)
  T3.5      — Launch validation (after all)
```
