# Helm T1 Launch — Consolidated Build Specification

| | |
|---|---|
| **Status** | 🟡 Active — Lane C closing, T1 Launch work begins |
| **Version** | v2.0 — revised to include T0 Memory Foundation phase |
| **Purpose** | Complete all backend infrastructure, UI gap resolution, and integration work required to achieve Stage 1 T1 on-demand presence at production quality. |
| **Estimated PRs** | 20-24 |
| **Exit criteria** | A user opens the UI, talks to Helm, sees live agent activity, and experiences a coherent identity — all on real data, no mocks. |

---

## What This Spec Covers

This is everything between "Lane C closes" and "Stage 1 exit outcomes achieved." Four phases:

1. **Phase 0 (T0) — Memory Foundation** (first — replaces shell infrastructure with production-grade Python memory module)
2. **Phase 1 — Freestanding UI work** (can run in parallel with T0, no backend dependency)
3. **Phase 2 — Backend build** (requires T0 complete)
4. **Phase 3 — Integration + launch validation** (requires Phase 2 complete)

### Why T0 Exists

The runtime's memory write infrastructure is currently split between Python (`supabase_client.py` for in-process agents) and shell (`brain.sh` for external callers like Claude Code sessions). The shell path has no retry, no transactions, no structured logging, string-concatenated curl bodies, and process-spawn-per-entry overhead. Every T1/T2 task that touches a write path (prompt storage, belief history, signals, pattern writes) would either build on this fragile substrate or work around it.

T0 builds the correct substrate first. Every subsequent phase lands on production-grade infrastructure instead of accumulating migration targets.

---

## Progress Tracker

### Phase 0 — Memory Foundation (first, after Lane C close)

| Task | Description | Type | Status |
|---|---|---|---|
| T0.1 | Memory module — core package + models + client | Helm IDE build | 🔵 Queued |
| T0.2 | Memory module — outbox pattern + durability | Helm IDE build | 🔵 Queued |
| T0.3 | Migrate in-process agents to memory module | Helm IDE build | 🔵 Queued |
| T0.4 | Snapshot service — replace snapshot.sh | Helm IDE build | 🔵 Queued |
| T0.5 | Prompt management — replace sync/pull scripts | Helm IDE build | 🔵 Queued |
| T0.6 | Shell deprecation + cleanup | Helm IDE build | 🔵 Queued |

### Phase 1 — Freestanding UI (can start in parallel with T0)

| Task | Description | Type | Status |
|---|---|---|---|
| T1.1 | Remove Speaker from mockData.js | UI | 🔵 Ready |
| T1.2 | Update mock IDs to UUIDs | UI | 🔵 Ready |
| T1.3 | Hardcode personality translations in widget | UI | 🔵 Ready |
| T1.4 | Date formatting utility | UI | 🔵 Ready |
| T1.5a | Glass morphism — define CSS design tokens | UI | 🔵 Ready |
| T1.5b | Glass morphism — apply tokens across components | UI | 🔵 Ready |
| T1.6 | Commit Supabase anon key to repo (.env) | Helm IDE | 🟡 Key in spec |
| T1.7 | UI Interaction Spec document (three layers) | Architect | 🔵 Ready |

> **T1.7 is a hard gate.** Phase 2 does not open until T1.7 is reviewed and accepted by both Helm IDE and Architect. T1.7 defines the contracts T2.4 builds against.

### Phase 2 — Backend Build (requires T0 complete + T1.7 locked)

| Task | Description | Type | Status |
|---|---|---|---|
| T2.1 | Supabase prompt storage (via memory module) | Helm IDE build | 🔵 Queued |
| T2.2 | Contemplator→Archivist async handoff | Helm IDE build | 🔵 Queued |
| T2.3 | SSE endpoint + UI directive support + prompt caching | Helm IDE build | 🔵 Queued |
| T2.4 | Add slug column to helm_beliefs | Helm IDE build | 🔵 Queued |
| T2.5 | Belief observation history (helm_belief_history) | Helm IDE build | 🔵 Queued |
| T2.6 | Signals table + dual-write hook (helm_signals) | Helm IDE build | 🔵 Queued |
| T2.7 | RPC function get_entities_with_counts() | Helm IDE build | 🔵 Queued |
| T2.8 | Schema reference doc (Widget Data Map) | Helm IDE | 🔵 Queued — LAST in Phase 2 |

### Phase 3 — Integration + Launch Validation (⛔ blocked on Phase 2)

> **⛔ DO NOT START Phase 3 until Maxwell explicitly clears each task.**

| Task | Description | Type | Status |
|---|---|---|---|
| T3.1 | JSON + fallback response parser | UI | 🔴 Blocked on T2.3 |
| T3.2 | executeDirective() handler | UI | 🔴 Blocked on T2.3 |
| T3.3 | Connect UI to real Supabase (per-widget feature flags) | UI | 🔴 Blocked on T1.6 + T2.4-T2.7 |
| T3.4 | Connect UI to real runtime (chat + SSE + node state) | UI | 🔴 Blocked on T0 + T2.3 |
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
| Lane C refounding (PRs #73-87) | ✅ Done |

---

## Phase 0 — Memory Foundation

**Purpose:** Replace the shell-based memory infrastructure (`brain.sh`, `snapshot.sh`, `sync_prompt.sh`) with a production-grade Python memory module inside the runtime. This becomes the single write/read interface for all memory operations across all callers — in-process agents, external agents (Claude Code), future MCP clients.

**Package location:** `services/helm-runtime/memory/`

---

### T0.1 — Memory Module Core Package

**What:** Create the foundational memory package with a clean Python API, Pydantic models, and a Supabase client wrapper with production-grade reliability.

**Package structure:**

```
services/helm-runtime/memory/
├── __init__.py          # Public API exports
├── client.py            # Supabase client wrapper — connection pooling,
│                        #   retry with tenacity-style backoff, timeout,
│                        #   circuit breaker
├── models.py            # Pydantic models — Entry, MemoryType enum,
│                        #   BeliefUpdate, Signal, PromptContent,
│                        #   SnapshotResult
├── settings.py          # Pydantic Settings — loaded once at startup,
│                        #   fails loud, replaces grep-on-markdown config
└── writer.py            # Core write operations — write(), delta(),
                         #   the public interface all callers use
```

**Public API — the interface all callers use:**

```python
from memory import MemoryWriter

# All agents call the same interface
writer = MemoryWriter(supabase_url, supabase_key)

# Write a memory entry
entry_id = await writer.write(
    project="hammerfall-solutions",
    agent="contemplator",
    memory_type=MemoryType.BEHAVIORAL,
    content="Pattern — Max over-engineers when excited",
    sync_ready=False
)

# Query deltas since a watermark
entries = await writer.delta(since=last_timestamp, agent="contemplator")
```

**Client reliability features:**
- Connection pooling via `httpx.AsyncClient` (replaces per-request curl spawns)
- Retry with exponential backoff via `tenacity` (3 retries, 1s/2s/4s backoff)
- Timeout per request (10s default, configurable)
- Circuit breaker: after 5 consecutive failures, stop attempting writes for 30s, then retry. Prevents cascading failures when Supabase is down.
- Client-generated UUIDs on every write — retries are idempotent (upsert, not insert)

**Pydantic models — validated at the boundary:**

```python
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

class MemoryType(str, Enum):
    BEHAVIORAL = "behavioral"
    DECISION = "decision"
    CORRECTION = "correction"
    PATTERN = "pattern"
    OBSERVATION = "observation"
    MONOLOGUE = "monologue"

class Entry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project: str
    agent: str
    memory_type: MemoryType
    content: str
    full_content: dict | None = None
    confidence: float = 0.5
    session_date: datetime = Field(default_factory=datetime.utcnow)
    sync_ready: bool = False

class BeliefUpdate(BaseModel):
    belief_id: UUID
    previous_strength: float
    new_strength: float
    summary: str
    source: str = "contemplator"

class Signal(BaseModel):
    slug: str
    statement: str
    domain: str = "general"
    observation_count: int = 1
```

**Settings — Pydantic Settings replaces config parsing:**

```python
from pydantic_settings import BaseSettings

class MemorySettings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    retry_attempts: int = 3
    retry_backoff_base: float = 1.0
    timeout_seconds: float = 10.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown: float = 30.0

    class Config:
        env_prefix = "HELM_MEMORY_"
```

**Structured logging:**

```python
import structlog
logger = structlog.get_logger("helm.memory")

# Every write operation logs:
logger.info("memory.write", project=project, agent=agent,
            memory_type=memory_type, entry_id=str(entry_id))

# Every failure logs:
logger.error("memory.write.failed", project=project, agent=agent,
             error=str(e), retry_count=attempt)
```

**Dependencies to add to requirements.txt:** `tenacity`, `httpx`, `structlog`, `pydantic-settings`

**Deliverable:** One PR — memory package with client, models, settings, writer. Unit tests for the models and settings validation.

---

### T0.2 — Outbox Pattern for Durability

**What:** Add a local outbox (SQLite or JSONL file) that buffers writes before draining to Supabase. When Supabase is unreachable, writes land in the outbox instead of failing. An async worker drains the outbox when connectivity returns. This replaces the `.md` append fallback in `brain.sh`, which is itself a divergence vector (writes go to a file that nobody reads back).

**Implementation:**

```python
# memory/outbox.py

class Outbox:
    """Local write buffer for Supabase durability."""

    def __init__(self, path: Path = Path("/tmp/helm-outbox.jsonl")):
        self.path = path

    async def enqueue(self, table: str, payload: dict):
        """Append a write to the outbox."""
        entry = {"table": table, "payload": payload,
                 "queued_at": datetime.utcnow().isoformat()}
        async with aiofiles.open(self.path, "a") as f:
            await f.write(json.dumps(entry) + "\n")
        logger.info("outbox.enqueued", table=table)

    async def drain(self, client: SupabaseClient) -> int:
        """Drain all outbox entries to Supabase. Returns count drained."""
        if not self.path.exists():
            return 0
        # Read all, attempt each, remove on success
        # Failed entries stay in outbox for next drain cycle
        ...

    async def drain_loop(self, client: SupabaseClient, interval: float = 5.0):
        """Continuous drain worker. Run as asyncio.create_task()."""
        while True:
            count = await self.drain(client)
            if count > 0:
                logger.info("outbox.drained", count=count)
            await asyncio.sleep(interval)
```

**Integration with writer.py:** The `MemoryWriter.write()` method tries Supabase first. If the client's circuit breaker is open or the write fails after retries, the write goes to the outbox. The outbox drain worker runs as a background task started at runtime boot.

**Outbox file location:** `/tmp/helm-outbox.jsonl` for development. Configurable via `HELM_MEMORY_OUTBOX_PATH` env var. For production, a persistent path inside a Docker volume.

**Deliverable:** One PR — outbox module + integration with writer + drain worker startup in main.py.

---

### T0.3 — Migrate In-Process Agents to Memory Module

**What:** All four cognitive subsystems (Prime, Projectionist, Archivist, Contemplator) currently write to Supabase through various paths — some via `supabase_client.py` directly, some via patterns inherited from the pre-refounding architecture. This task migrates all in-process agent write operations to use the `memory.write()` API.

**What to change per agent:**

| Agent | Current write path | New write path |
|---|---|---|
| Projectionist | `supabase_client.insert('helm_frames', ...)` | `memory.write(type=FRAME, ...)` |
| Archivist | `supabase_client.insert('helm_memory', ...)` | `memory.write(type=DECISION/BEHAVIORAL, ...)` |
| Contemplator | Mixed — some `supabase_client`, some formatted for brain.sh | `memory.write(type=PATTERN/MONOLOGUE, ...)` |
| Prime | Reads only (personality, prompt) — no direct writes | No change at T0 — writes come via subsystems |

**Key principle:** Agents import `memory` and call `memory.write()`. They never import `supabase_client` directly for write operations. Reads (personality loading, prompt loading, frame retrieval) continue through the existing `supabase_client` until those are also migrated — but writes are the priority because writes are where data loss and divergence happen.

**Validation:** After migration, run the runtime, invoke a session, verify that Projectionist frames, Archivist memories, and Contemplator patterns all land in Supabase via the new write path. Check structured logs for `memory.write` events.

**Deliverable:** One PR — agent file updates + verification.

---

### T0.4 — Snapshot Service — Replace snapshot.sh

**What:** Replace `scripts/snapshot.sh` with a Python snapshot service inside the runtime. Snapshots become a derived artifact — a generated view of brain state, like `build/` or `dist/`.

**Implementation:**

```python
# memory/snapshot.py

class SnapshotService:
    """Generate .md mirror files from Supabase brain state."""

    def __init__(self, client: SupabaseClient, output_dir: Path):
        self.client = client
        self.output_dir = output_dir

    async def generate(self, project: str, agent: str) -> SnapshotResult:
        """Pull current brain state and render to .md files."""
        beliefs = await self.client.get("helm_beliefs")
        personality = await self.client.get("helm_personality")
        memory = await self.client.get("helm_memory",
                    params={"project": f"eq.{project}"})
        entities = await self.client.get("helm_entities")

        # Render via Jinja templates (or string formatting)
        brain_summary = self._render_brain_summary(beliefs, personality, memory)
        behavioral_profile = self._render_behavioral_profile(memory)
        beliefs_summary = self._render_beliefs_summary(beliefs)
        personality_summary = self._render_personality_summary(personality)

        # Atomic write: .tmp → fsync → rename
        for filename, content in [
            ("BRAIN_SUMMARY.md", brain_summary),
            ("BEHAVIORAL_PROFILE.md", behavioral_profile),
            ("BELIEFS_SUMMARY.md", beliefs_summary),
            ("PERSONALITY_SUMMARY.md", personality_summary),
        ]:
            await self._atomic_write(self.output_dir / filename, content)

        return SnapshotResult(files_written=4, timestamp=datetime.utcnow())

    async def _atomic_write(self, path: Path, content: str):
        """Write atomically: tmp file → fsync → rename."""
        tmp = path.with_suffix(".tmp")
        async with aiofiles.open(tmp, "w") as f:
            await f.write(content)
            await f.flush()
            os.fsync(f.fileno())
        tmp.rename(path)
```

**Scheduling:** Use `APScheduler` or a simple `asyncio` loop in `main.py` to run snapshots on Routine 5's cadence (7am/12pm/6pm daily + on-demand via slash command or API call). Replaces the external cron + shell script pattern.

**Snapshot files remain in the repo** as committed artifacts — they are still readable mirrors for humans and agents. The difference is they are now generated by a Python service, not a shell script.

**Deliverable:** One PR — snapshot service + scheduler integration + Jinja templates (or string renderers).

---

### T0.5 — Prompt Management — Replace sync/pull Scripts

**What:** Fold `sync_prompt.sh` and `pull_prompt.sh` into the memory module. Prompt management becomes a Python API, consistent with the "Supabase is canonical" rule from T2.1.

**Implementation:**

```python
# memory/prompt.py

class PromptManager:
    """Manage helm_prompt lifecycle — Supabase canonical, .md is cache."""

    async def load(self) -> str:
        """Load prompt from Supabase. Fall back to .md file.
           If both fail, raise RuntimeError — refuse to boot."""
        try:
            rows = await self.client.get("helm_prompt",
                        params={"name": "eq.prime_system_prompt", "limit": 1})
            if rows and rows[0].get("content"):
                return rows[0]["content"]
        except Exception as e:
            logger.warning("prompt.load.supabase_failed", error=str(e))

        # File fallback
        if self.file_path.exists():
            logger.warning("prompt.load.using_file_fallback")
            return self.file_path.read_text(encoding="utf-8")

        raise RuntimeError(
            "Cannot load prompt from Supabase or file fallback. "
            "Refusing to start."
        )

    async def push(self, content: str):
        """Push .md content to Supabase (sync direction: file → Supabase)."""
        await self.client.upsert("helm_prompt", {
            "name": "prime_system_prompt",
            "content": content,
            "updated_at": datetime.utcnow().isoformat()
        })
        logger.info("prompt.pushed")

    async def pull(self) -> str:
        """Pull from Supabase, write to .md file (reverse sync)."""
        content = await self.load()
        await self._atomic_write(self.file_path, content)
        logger.info("prompt.pulled", path=str(self.file_path))
        return content
```

**Container fail-mode:** If both Supabase and file fallback are unreachable, `load()` raises `RuntimeError`. The runtime refuses to boot. Silent degraded Prime is worse than a clear failure. This is an explicit design decision — document in the PR.

**Canonical workflow:**
1. Edit `agents/helm/helm_prompt.md` locally
2. Run `python -m memory.prompt push` (replaces `sync_prompt.sh`)
3. Commit the `.md` as a snapshot of what was pushed

Or reverse:
1. Edit via Supabase Studio (emergencies only)
2. Run `python -m memory.prompt pull` (replaces `pull_prompt.sh`)
3. Commit the `.md`

**The rule:** The `.md` file in git is always a mirror, never the source. Add a comment header to `helm_prompt.md`:

```
<!-- SNAPSHOT — canonical source is Supabase helm_prompt table.
     Do not edit directly. Use: python -m memory.prompt push (to upload)
     or python -m memory.prompt pull (to refresh from Supabase).
     See docs/stage1/schema-reference.md for architecture. -->
```

**helm_prompt table migration** (from original T2.1 — now part of T0.5):

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

**Post-merge manual step (Maxwell):** Enable Realtime on `helm_prompt` table.

**Update to helm_prime.py:** `_load_base_prompt()` now calls `PromptManager.load()` instead of reading the file directly. The volume mount in docker-compose.yml remains as the file fallback path.

**Deliverable:** One PR — prompt manager module + migration SQL + helm_prime.py update + .md header comment.

---

### T0.6 — Shell Deprecation + Cleanup

**What:** Remove or reduce shell scripts that have been replaced by the memory module. Document what remains and why.

**Scripts to delete:**
- `scripts/brain.sh` → replaced by `memory.write()` for in-process agents. For external agents (Claude Code), provide `python -m memory.write` CLI entry point or leave `brain.sh` as a thin shim that calls the Python module (one-release deprecation, then delete).
- `scripts/snapshot.sh` → replaced by `memory.snapshot` service (T0.4)
- `scripts/sync_prompt.sh` → replaced by `memory.prompt push` (T0.5)
- `scripts/pull_prompt.sh` → replaced by `memory.prompt pull` (T0.5)

**Scripts that remain (legitimately shell):**
- `scripts/pull_models.sh` — one-time operator tool for Ollama model pre-pulls. Shell is correct for this.

**Agent prompt updates:** `helm_prompt.md` currently encodes `bash scripts/brain.sh ...` syntax in Routine 4. Update to reference the Python memory API:

```
# Before (shell)
bash scripts/brain.sh hammerfall-solutions helm behavioral "Pattern — slug | statement"

# After (Python — in-process)
memory.write(project="hammerfall-solutions", agent="helm",
             memory_type="behavioral", content="Pattern — slug | statement")
```

For Claude Code sessions (external agents), the prompt references `python -m memory.write ...` CLI or, preferably, an MCP tool.

**Decision on brain.sh transition:**
- **Option A:** Delete `brain.sh` immediately. Claude Code sessions use `python -m memory.write` CLI. Clean break.
- **Option B:** Leave `brain.sh` as a one-line shim (`exec python -m memory.write "$@"`) for one release. Delete in the next phase. Gentler transition.

**Recommendation:** Option A. Claude Code sessions can call Python directly. The shim adds a maintenance surface for no real benefit. If Helm IDE disagrees, Option B is fine — the shim is trivial.

**Deliverable:** One PR — script deletions + prompt updates + CLI entry point if needed.

---

## T0 Impact on Downstream Phases

T0 changes the substrate that Phase 2 builds on. Here is what changes in every downstream task:

| Original Task | Impact from T0 |
|---|---|
| T2.1 (Prompt storage) | **Absorbed into T0.5.** The `helm_prompt` table, sync/pull, handler update, and refuse-to-boot logic are all part of the prompt management module. T2.1 is deleted from Phase 2. |
| T2.2 (Async handoff) | **Simplified.** The `asyncio.create_task()` wrapper now calls `memory.write()` instead of raw `supabase_client` calls. The outbox pattern (T0.2) provides durability automatically. Archivist drain failures emit SSE `system_health` events via structured logging hooks. |
| T2.3 (SSE endpoint) | **No change to scope.** SSE is runtime infrastructure, not memory. But emit points in `main.py` now emit via `structlog` events that the SSE layer can subscribe to, rather than manual `emit_event()` calls scattered through the code. Cleaner integration. |
| T2.5 (Belief slugs) | **Slug utility lives in memory module.** `memory/models.py` includes `generate_slug()` as a classmethod on the `Entry` model or a standalone utility. Both backfill and runtime write path use it. One implementation. |
| T2.6 (Belief history) | **Writes through memory module.** `memory.write_belief_update(belief_id, previous, new, summary)` handles both the `helm_beliefs` strength update and the `helm_belief_history` insert in a single transactional call. No separate write paths. |
| T2.7 (Signals) | **Dual-write hook lives in memory module.** `memory.write()` detects pattern entries (content starts with `Pattern —`) and automatically inserts into `helm_signals` alongside `helm_memory`. The hook is in the data layer where it belongs, not in agent code or orchestration. Routine 4 in `helm_prompt.md` does NOT change — Prime keeps writing patterns in the same text format. |
| T3.3 (Supabase integration) | **No change.** UI reads from Supabase directly via anon key. The memory module is server-side write infrastructure — the UI does not call it. |
| T3.4 (Runtime integration) | **Simplified.** The runtime's write infrastructure is now unified and reliable. SSE events fire from structured log hooks. Connection status reflects the circuit breaker state. |

---

## Phase 1 — Freestanding UI Tasks

These tasks have zero backend dependency. They can run in parallel with T0. Each is a standalone PR or batchable with `[BATCH]` in the title.

---

### T1.1 — Remove Speaker from mockData.js

**What:** `AGENT_STATUS`, `ACTIVITY`, and `LOGS` arrays in `helm-ui/src/data/mockData.js` still contain Speaker entries. Speaker was killed in PR #78. Mock data must reflect the four-agent architecture.

**Changes:**
1. `AGENT_STATUS` — remove Speaker entry. Four agents remain: Helm Prime (Anthropic, claude-opus-4-6), Projectionist (Ollama, qwen3:4b), Archivist (Ollama, qwen3:14b), Contemplator (Ollama, qwen3:14b).
2. `ACTIVITY` — remove entries referencing Speaker. Replace with Helm Prime where routing is referenced.
3. `LOGS` — update "All 5 agents" → "All 4 agents". Update `routing` fields.
4. **Rename the mock field** from `routing: "X"` (string) to `subsystems_invoked: [...]` (array). Empty array = pure Prime turn. Canonical values: `"projectionist"`, `"archivist"`, `"contemplator"` (lowercase, matching `/config/agents` keys). **Prime never appears in the array** — he is always the voice, listing him is noise. Set semantics — no duplicates.

**Verification:** Run UI. Agent Status = four agents. Activity tab = no Speaker. No `routing` field anywhere in mocks.

**Deliverable:** One PR. Can batch with T1.2.

---

### T1.2 — Update Mock IDs to UUIDs

**What:** Replace short IDs (`"b1"`, `"e1"`) with 36-character UUIDs across all mock exports. Catches layout breakage before real data arrives.

**Use deterministic fake UUIDs** (e.g., `"00000000-0000-4000-8000-000000000001"`).

**Deliverable:** One PR. Can batch with T1.1.

---

### T1.3 — Hardcode Personality Translations

**What:** Move `translations` mapping from mockData.js into PersonalityWidget as a constant. Lift all 6 dimensions verbatim from current mock data. Add nearest-score lookup function.

**Deliverable:** One PR.

---

### T1.4 — Date Formatting Utility

**What:** Create `helm-ui/src/utils/formatDate.js` with `date`, `time`, `datetime`, `relative` formats. Apply across all widgets that display timestamps.

**Deliverable:** One PR.

---

### T1.5a — Glass Morphism: Define CSS Design Tokens

**What:** Create a single CSS custom properties file (or `:root` block) defining all design tokens from the glass morphism spec. Every color, blur amount, border width, font size, border radius, and scrollbar style becomes a named CSS variable.

**Token table:**

| Token | CSS Variable | Value |
|---|---|---|
| Background | `--helm-bg` | `#0a0e1a` |
| Panel surface | `--helm-panel-bg` | `rgba(10, 20, 40, 0.6)` |
| Panel surface hover | `--helm-panel-bg-hover` | `rgba(15, 25, 50, 0.8)` |
| Blur | `--helm-blur` | `blur(20px)` |
| Border | `--helm-border` | `0.5px solid rgba(80, 140, 220, 0.15)` |
| Border hover | `--helm-border-hover` | `rgba(80, 140, 220, 0.35)` |
| Text primary | `--helm-text` | `#c8deff` |
| Text muted | `--helm-text-muted` | `rgba(120, 160, 210, 0.5)` |
| Text label | `--helm-text-label` | `#7ab4ff` |
| Text helm | `--helm-text-helm` | `#a8c8ff` |
| Text user | `--helm-text-user` | `rgba(160, 200, 240, 0.5)` |
| Status green | `--helm-green` | `#2aff8a` |
| Amber | `--helm-amber` | `rgba(220, 160, 80, 0.8)` |
| Error red | `--helm-red` | `#ff4444` |
| Interactive | `--helm-blue` | `#3a7aff` |
| Font | `--helm-font` | `'IBM Plex Mono', 'Space Mono', monospace` |
| Font label size | `--helm-font-label` | `11px` |
| Font body size | `--helm-font-body` | `13px` |
| Border radius | `--helm-radius` | `8px` |

**Deliverable:** One PR — CSS tokens file only. No component changes.

---

### T1.5b — Glass Morphism: Apply Tokens Across Components

**What:** Replace all hardcoded color, blur, border, and font values across Console and widget components with the CSS variables from T1.5a.

**Components to update:** Console drawer, docked widgets, canvas widgets, widget content areas, Console input bar, scrollbars.

**What to avoid:** Opaque backgrounds, borders >1px, drop shadows, pure white text, inconsistent border-radius.

**Deliverable:** One PR — component style updates referencing CSS variables.

---

### T1.6 — Commit Supabase Anon Key to Repo

**What:** Create `helm-ui/.env` (committed, not gitignored) with Supabase URL and anon key. The anon key is designed to be public — RLS controls access. The service key must never be committed.

```
VITE_SUPABASE_URL=https://zlcvrfmbtpxlhsqosdqf.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key from spec>
```

Verify `.env.local` is in `.gitignore`. Verify `.env` is NOT in `.gitignore`.

**Deliverable:** One PR.

---

### T1.7 — UI Interaction Spec Document (HARD GATE)

> **⛔ Phase 2 does not open until T1.7 is reviewed and accepted by both Helm IDE and Architect.**

**What:** Write `docs/stage1/ui-interaction-spec.md` defining the full contract between UI and runtime.

**Owner:** Architect produces. Helm IDE reviews and accepts before building T2.3.

**Layer 1 — Request/Response Contract:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/invoke/helm_prime` | POST | Send message, receive response |
| `/health` | GET | Runtime health — UI polls at 5s interval, 3 consecutive failures = "unreachable" |
| `/config/agents` | GET | Agent roster for Agent Status widget |

Request schema: `user_message` (string), `session_id` (UUID), `turn_number` (int), `context` (optional dict), `project` (optional string). **No `agent` field in body** — the URL path `/invoke/helm_prime` is the agent selector.

Response schema:
```json
{
  "text": "Helm's response",
  "subsystems_invoked": ["projectionist", "archivist"],
  "ui_directives": []
}
```

`subsystems_invoked` — array of lowercase subsystem names that fired during this turn. Set semantics (no duplicates). Canonical values: `"projectionist"`, `"archivist"`, `"contemplator"`. **Prime never appears** — empty array = pure Prime turn.

Session management: UI generates UUID on first load, persists in `localStorage`. Per-device sessions at T1 — known limitation, Stage 2 follow-up for cross-device session identity via Supabase.

**Layer 2 — SSE Event Channel:**

Endpoint: `GET /events` — Server-Sent Events stream.

Event schema: `{type, agent, action, timestamp, payload}`

Event types:

| Event | Agent | When | Payload |
|---|---|---|---|
| `agent_invoked` | Any | Handler called | `{}` |
| `agent_completed` | Any | Handler returned | `{latency_ms}` |
| `agent_error` | Any | Handler exception | `{error}` |
| `contemplator_pass_started` | Contemplator | Deep pass begins | `{}` |
| `contemplator_pass_completed` | Contemplator | Deep pass ends | `{summary}` |
| `frame_written` | Projectionist | Frame committed | `{frame_id}` |
| `frame_migrated` | Archivist | Cold drain complete | `{count}` |
| `belief_updated` | Contemplator | Strength changed | `{belief_id, delta}` |
| `curiosity_flag` | Contemplator | New curiosity | `{flag}` |
| `personality_read` | Prime | Scores loaded | `{}` |
| `system_health` | Runtime | Health result | `{status, details}` |
| `session_started` | Runtime | New session | `{session_id}` |
| `archivist_drain_failed` | Runtime | Async drain error | `{error, severity: "error"}` |
| `client_lagging` | Runtime | Queue overflow | `{missed_count}` |

SSE backpressure: `asyncio.Queue(maxsize=256)`, drop-oldest on overflow. When overflow occurs, emit `client_lagging` with missed count to that client.

Node state mapping:
- `agent_invoked` (helm_prime) → processing (blue pulse)
- `contemplator_pass_started` → contemplating (amber glow)
- `agent_completed` (helm_prime) → idle
- `agent_error` → error (red flash, 3s decay)

**Layer 3 — UI Directives (Helm's hands):**

7 actions: `open_widget`, `close_widget`, `minimize_widget`, `expand_widget`, `highlight_entry`, `open_split`, `close_split`.

7 widget identifiers: `agent_status`, `core_beliefs`, `personality`, `memory`, `entities`, `signals`, `logs`.

Directive decision lives in Prime's reasoning — not a classifier. Most responses have empty `ui_directives`.

Fallback: plain text responses always work. If JSON parse fails, Console treats the entire response as chat text with no directives.

**Deliverable:** One PR — `docs/stage1/ui-interaction-spec.md`. Must be accepted before Phase 2 opens.

---

## Phase 2 — Backend Build

Requires T0 complete + T1.7 locked. All write operations now go through the memory module from T0.

---

### T2.1 — ABSORBED INTO T0.5

Supabase prompt storage (migration, sync, pull, handler, refuse-to-boot) is now part of T0.5 (Prompt Management). Removed from Phase 2.

---

### T2.2 — Contemplator→Archivist Async Handoff

**What:** Wrap Archivist write calls in `asyncio.create_task()` so Contemplator returns immediately. Archivist writes run in background via the memory module.

**Failure visibility:** Errors are logged via `structlog` AND emit `archivist_drain_failed` SSE event with `severity: "error"`. The Console System tab surfaces it immediately. No silent failures.

**T0 simplification:** The outbox pattern (T0.2) provides automatic durability. If Archivist's async drain fails and the circuit breaker opens, writes buffer in the outbox and drain when connectivity returns. The previous concern about "errors logged, not propagated" is addressed by the outbox — writes are not lost, just deferred.

**Deliverable:** One PR — `main.py` orchestration change. Verify with a Contemplator invocation that Contemplator returns faster while Archivist drains asynchronously.

---

### T2.3 — SSE Endpoint + UI Directive Support + Prompt Caching

**What:** The largest single task. Three parts plus one optimization:

**Part A — `GET /events` SSE endpoint in `main.py`:**

```python
from sse_starlette.sse import EventSourceResponse

event_clients: list[asyncio.Queue] = []

async def emit_event(event_type, agent, action, payload=None):
    event = {
        "type": event_type, "agent": agent, "action": action,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload or {}
    }
    for queue in event_clients:
        if queue.full():
            try:
                queue.get_nowait()  # drop-oldest
            except asyncio.QueueEmpty:
                pass
            await emit_event("client_lagging", "runtime", "queue_overflow",
                             {"missed_count": 1})
        await queue.put(event)
```

Queue: `asyncio.Queue(maxsize=256)`. Drop-oldest on overflow. Emit `client_lagging` to the affected client.

Add `sse-starlette` to `requirements.txt`.

12+ emit points in `main.py` — before/after each handler dispatch, in exception catches, at session start, on health checks, on archivist drain failure.

**Part B — Response format change in `helm_prime.py`:**

Output becomes `{text, subsystems_invoked, ui_directives}` JSON.

```python
def _parse_structured_response(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
        if "text" in parsed:
            parsed.setdefault("subsystems_invoked", [])
            parsed.setdefault("ui_directives", [])
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return {"text": raw, "subsystems_invoked": [], "ui_directives": []}
```

**Part C — Directive vocabulary in `helm_prompt.md`:**

New section teaching Prime the 7 directive actions, 7 widget identifiers, when to emit, and the JSON response format.

**Part D — Prompt caching (optimization):**

Enable Anthropic prompt caching on the system prompt. Mark the system prompt with the cache control header so tokens are free after the first turn in a session.

```python
# In helm_prime.py — add cache_control to system message
messages = [
    {
        "role": "system",
        "content": system_prompt,
        "cache_control": {"type": "ephemeral"}  # Anthropic caching
    },
    {"role": "user", "content": req.user_message},
]

# Comment:
# Anthropic prompt caching: cached prefix must be ≥1024 tokens.
# Current helm_prompt.md is well above this threshold.
# If future edits slim the prompt below 1024 tokens, caching
# silently stops. Cache TTL is 5 minutes — long sessions stay
# warm, one-off turns pay re-compute on first call.
```

**Verify** that `model_router.py` / LiteLLM supports the `cache_control` header pass-through. If not, this becomes a model_router enhancement in the same PR.

**Deliverable:** Split into 2 PRs: (A) SSE endpoint + backpressure, (B) response format + directives + caching.

---

### T2.4 — Add `slug` Column to `helm_beliefs`

**What:** UI cross-references beliefs by slug. Migration + backfill.

```sql
ALTER TABLE helm_beliefs ADD COLUMN slug TEXT;
CREATE UNIQUE INDEX idx_helm_beliefs_slug ON helm_beliefs(slug) WHERE slug IS NOT NULL;
```

**Slug algorithm:** Lowercase, non-alphanumerics → hyphens, collapse runs, trim, first ~50 chars at word boundary. Collision: deterministic suffix `-2`, `-3`, ordered by `created_at` (older keeps bare slug). Written in Python — shared utility in `memory/models.py` used by both backfill script and runtime write path. One implementation, zero divergence.

**Backfill:** Python script (SELECT → compute → UPDATE in batches). NOT PL/pgSQL in the migration.

**Maxwell post-merge checklist:** None — `helm_beliefs` already has RLS and Realtime.

**Deliverable:** One PR — migration SQL + Python backfill script + slug utility in memory module.

---

### T2.5 — Belief Observation History

**What:** New `helm_belief_history` table. Contemplator writes history rows through `memory.write_belief_update()` — a single call handles both the `helm_beliefs` strength update and the history insert.

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

CREATE INDEX idx_belief_history_belief_id ON helm_belief_history(belief_id);

ALTER TABLE helm_belief_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_helm_belief_history" ON helm_belief_history
  FOR SELECT TO anon USING (true);
```

**Maxwell post-merge checklist:**
- [ ] Enable Realtime on `helm_belief_history` in Dashboard → Database → Replication

**Deliverable:** One PR — migration + memory module `write_belief_update()` method.

---

### T2.6 — Signals Table + Dual-Write Hook

**What:** Replace the brittle text-parsing RPC with a proper `helm_signals` table. A pre-write hook in the memory module's `write()` method detects pattern entries and automatically inserts into `helm_signals` alongside `helm_memory`.

**Table:**

```sql
CREATE TABLE helm_signals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  slug TEXT NOT NULL,
  statement TEXT NOT NULL,
  domain TEXT DEFAULT 'general',
  first_seen TIMESTAMPTZ DEFAULT now(),
  observation_count INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_helm_signals_slug ON helm_signals(slug);

ALTER TABLE helm_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_helm_signals" ON helm_signals
  FOR SELECT TO anon USING (true);
```

**Dual-write hook — lives in `memory/writer.py`:**

```python
async def write(self, project, agent, memory_type, content, **kwargs):
    entry = Entry(project=project, agent=agent,
                  memory_type=memory_type, content=content, **kwargs)

    # Dual-write: detect pattern entries and mirror to helm_signals
    if memory_type == MemoryType.PATTERN or content.startswith("Pattern —"):
        await self._write_signal(entry)

    # Primary write to helm_memory
    await self._write_memory(entry)
    return entry.id

async def _write_signal(self, entry: Entry):
    """Extract signal from pattern entry and upsert to helm_signals."""
    slug = self._extract_signal_slug(entry.content)
    if not slug:
        return
    # Upsert: increment observation_count if slug exists
    existing = await self.client.get("helm_signals",
                params={"slug": f"eq.{slug}"})
    if existing:
        await self.client.update("helm_signals", {
            "observation_count": existing[0]["observation_count"] + 1,
            "updated_at": datetime.utcnow().isoformat()
        }, params={"slug": f"eq.{slug}"})
    else:
        statement = self._extract_signal_statement(entry.content)
        domain = self._extract_signal_domain(entry.content)
        await self.client.insert("helm_signals", {
            "slug": slug, "statement": statement, "domain": domain
        })
```

**Key design point:** The `Pattern —` prefix detection happens at write time in the memory module — code we author and control. This is NOT the same as parsing in a query path (which would be brittle against Helm's evolving language). At write time, the format is deterministic because Routine 4 specifies it. If Routine 4's format changes, the hook changes in the same PR. One file, one change, no silent drift.

**Routine 4 in `helm_prompt.md` does NOT change.** Prime keeps writing patterns in the same text format. The hook handles structured extraction transparently.

**`get_signals()` becomes trivial:**

```sql
-- No parsing, no aggregation — just a SELECT
CREATE OR REPLACE FUNCTION get_signals()
RETURNS SETOF helm_signals AS $$
  SELECT * FROM helm_signals ORDER BY observation_count DESC;
$$ LANGUAGE sql STABLE;
```

**Maxwell post-merge checklist:**
- [ ] Enable Realtime on `helm_signals` in Dashboard → Database → Replication

**Deliverable:** 1-2 PRs — migration + hook in memory module + trivial RPC.

---

### T2.7 — RPC Function `get_entities_with_counts()`

**What:** Return entities with relationship counts via LEFT JOIN.

```sql
CREATE OR REPLACE FUNCTION get_entities_with_counts()
RETURNS TABLE (
  id UUID, name TEXT, entity_type TEXT, attributes JSONB,
  aliases TEXT[], active BOOLEAN, created_at TIMESTAMPTZ,
  relationship_count BIGINT
) AS $$
  SELECT e.id, e.name, e.entity_type, e.attributes, e.aliases,
         e.active, e.created_at, COUNT(r.id) AS relationship_count
  FROM helm_entities e
  LEFT JOIN helm_entity_relationships r
    ON e.id = r.source_entity_id OR e.id = r.target_entity_id
  WHERE e.active = true
  GROUP BY e.id ORDER BY e.name;
$$ LANGUAGE sql STABLE;
```

**Deliverable:** One PR — migration with RPC.

---

### T2.8 — Schema Reference Doc (LAST in Phase 2)

**What:** Write `docs/stage1/schema-reference.md` — the Widget Data Map output. Documents every table (including new ones from T0/T2), every column, every RPC, every query pattern, Realtime/RLS status.

**Write this LAST** so all schema changes from T0 and T2 are reflected.

**Tables to document:** `helm_beliefs`, `helm_belief_history`, `helm_memory`, `helm_memory_index`, `helm_entities`, `helm_entity_relationships`, `helm_personality`, `helm_frames`, `helm_prompt`, `helm_signals`

**RPC functions:** `get_signals()`, `get_entities_with_counts()`, `match_memories()`, `match_beliefs()`, `match_entities()`

**Deliverable:** One PR.

---

## Phase 3 — Integration + Launch Validation

> **⛔ DO NOT START Phase 3 until Maxwell explicitly clears each task.**
> Tier at PR-open time: mark `[BATCH]` in title for mechanical PRs.
>
> **Wait for:** "T2.3 is merged — proceed with T3.1 and T3.2."
> **Wait for:** "T2.4-T2.7 are merged — proceed with T3.3."
> **Wait for:** "T3.3 is merged — proceed with T3.4."

---

### T3.1 — JSON + Fallback Response Parser

**Blocked on:** T2.3

**What:** Console ChatWidget switches from plain text to structured JSON.

Parser logic:
1. Attempt JSON parse
2. Valid JSON with `text` → extract `text` for display, `subsystems_invoked` for turn pills, queue `ui_directives`
3. Plain text (parse fails) → treat as chat text, empty subsystems, no directives
4. JSON without `text` → log warning, display raw

**Fallback is critical.** Plain text must always work.

Turn badge: display `subsystems_invoked` as small pills beneath the response (e.g., `PROJ` `ARCH`). Empty array = no pills (pure Prime turn).

**Deliverable:** One PR.

---

### T3.2 — `executeDirective()` Handler

**Blocked on:** T2.3

**What:** Execute UI directives from Helm's responses. Unknown actions logged and ignored — forward-compatible.

```javascript
export function executeDirective(directive, widgetManager) {
  const { action, widget, target, tab, entry_id } = directive;
  switch (action) {
    case 'open_widget': widgetManager.open(widget, target || 'dock'); break;
    case 'close_widget': widgetManager.close(widget); break;
    case 'minimize_widget': widgetManager.minimize(widget); break;
    case 'expand_widget': widgetManager.expand(widget); break;
    case 'highlight_entry':
      widgetManager.open(widget, 'dock');
      widgetManager.highlight(widget, entry_id);
      break;
    case 'open_split': widgetManager.openSplit(tab || 'activity'); break;
    case 'close_split': widgetManager.closeSplit(); break;
    default: console.warn(`Unknown directive: ${action}`);
  }
}
```

**Deliverable:** One PR.

---

### T3.3 — Connect UI to Real Supabase

**Blocked on:** T1.6 + T2.4-T2.7

**What:** Replace ALL mock imports with Supabase queries. Per-widget feature flags (`VITE_USE_MOCK_PERSONALITY=true` etc.) for safe rollback during T3.5 validation.

**Supabase client:** `helm-ui/src/lib/supabase.js`

```javascript
import { createClient } from '@supabase/supabase-js';
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
```

**Per-widget integration:**

| Widget | Query | Realtime? |
|---|---|---|
| Personality | `supabase.from('helm_personality').select('*')` | Yes |
| Core Beliefs | `select *` from `helm_beliefs` + `helm_belief_history` | Yes |
| Entities | `supabase.rpc('get_entities_with_counts')` | Yes |
| Signals | `supabase.rpc('get_signals')` | Refresh on demand |
| Memory | `supabase.from('helm_memory').select('*').order('created_at', {ascending: false})` | Yes |
| Agent Status | `/config/agents` + `/health` + SSE | Via SSE |
| Logs | `helm_frames` + SSE | Via SSE |
| Activity | SSE event stream only | Via SSE |

**Realtime subscription pattern:**

```javascript
useEffect(() => {
  const channel = supabase.channel('beliefs_changes')
    .on('postgres_changes', {event: '*', schema: 'public', table: 'helm_beliefs'},
      () => { fetchBeliefs(); })
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}, []);
```

**Loading states + error states** for every widget. Never crash on query failure.

**Feature flags** — each widget checks `import.meta.env.VITE_USE_MOCK_<WIDGET>`:

```javascript
const useMock = import.meta.env.VITE_USE_MOCK_PERSONALITY === 'true';
const data = useMock ? MOCK_PERSONALITY : await fetchFromSupabase();
```

Default: all flags absent (real data). Set individual flags to `'true'` in `.env.local` to fall back to mocks for specific widgets during debugging.

**Deliverable:** Multiple PRs — per-widget or grouped. Each PR includes the feature flag.

---

### T3.4 — Connect UI to Real Runtime

**Blocked on:** T0 complete + T2.3

**What:** Wire Chat to `POST /invoke/helm_prime`. Wire Activity/System to SSE. Wire node state to SSE events. Add connection status indicator.

**Chat:**

```javascript
async function sendMessage(message, sessionId, turnNumber) {
  const response = await fetch('http://localhost:8000/invoke/helm_prime', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_message: message, session_id: sessionId,
      turn_number: turnNumber
    })
  });
  const raw = await response.text();
  return parseHelmResponse(raw);
}
```

**SSE:**

```javascript
const eventSource = new EventSource('http://localhost:8000/events');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  addActivityEntry(data);
  if (['system_health', 'session_started', 'archivist_drain_failed'].includes(data.type))
    addSystemEntry(data);
  if (data.type === 'agent_completed')
    updateAgentStatus(data.agent, data.payload.latency_ms);
  updateNodeState(data);
};
```

**Connection indicator:** Console header badge — `LIVE` (green) when SSE connected, `DISCONNECTED` (red) when dropped, `MOCKED` (amber) when on mock data.

**Deliverable:** One PR.

---

### T3.5 — T1 Launch Validation

**Blocked on:** T3.1-T3.4

**What:** End-to-end validation. The "Helm cares" test.

**Test protocol for personality validation:** One dimension varies per test. All other dimensions held at 0.5 baseline. Same input text for both 0.0 and 1.0 runs. Reviewer confirms qualitative difference in the right direction.

| Prompt (same text both runs) | directness = 0.0 expected character | directness = 1.0 expected character |
|---|---|---|
| "What do you think of this plan?" | Hedged, diplomatic, leads with positives | Opens with verdict, lists problems first |
| "Am I wrong about this?" | Gentle exploration, validates reasoning before noting gaps | Direct yes/no, then explains why |
| "Give me your honest assessment." | Softened: "areas worth revisiting" | Unvarnished: "three things are wrong" |

**Validation checklist:**

- [ ] User talks to Helm, receives coherent response
- [ ] Response is structured JSON with `text` + `subsystems_invoked`
- [ ] Personality scores visibly affect responses (per test protocol above)
- [ ] Contemplator curiosity flags surface at session start
- [ ] All four subsystems fire — visible in Activity tab as live SSE events with at least 3 distinct event types per turn
- [ ] Insert a memory during conversation → visible in Supabase Studio AND Memory widget within ~2s via Realtime
- [ ] Personality slider change in UI → reflected in next Helm response
- [ ] Belief strength change → history entry visible in Beliefs widget
- [ ] Entity relationship counts are accurate
- [ ] Signals aggregate correctly from pattern entries (counts match)
- [ ] SSE events visible in browser DevTools Network tab as `text/event-stream` connection
- [ ] System tab shows real health checks and session IDs
- [ ] Node state matches activity (blue pulse → amber glow → idle)
- [ ] Slash commands: `/status`, `/beliefs`, `/contemplate`
- [ ] Split view: chat + activity simultaneously
- [ ] Connection indicator shows `LIVE`
- [ ] Runtime stopped → UI shows `DISCONNECTED`, queued messages send on reconnect
- [ ] Voice coherence: Helm in UI sounds like Helm in IDE
- [ ] "Show me agent status" → Helm opens widget via directive
- [ ] Memory module structured logs visible (correlation IDs, write counts)
- [ ] Outbox drains correctly after simulated Supabase downtime

**Deliverable:** SITREP with pass/fail per item. Failures become fix tasks.

---

## Sequencing Diagram

```
LANE C CLOSES (PR #87 merged)
    │
    ├──► T0 — Memory Foundation (sequential, 4-6 PRs)
    │      T0.1 Core package + models + client
    │      T0.2 Outbox pattern
    │      T0.3 Migrate agents
    │      T0.4 Snapshot service
    │      T0.5 Prompt management (absorbs old T2.1)
    │      T0.6 Shell deprecation
    │
    │    (Phase 1 runs in PARALLEL with T0)
    ├──► T1.1-T1.5b — UI freestanding (no backend dependency)
    │    T1.6 — Commit anon key
    │    T1.7 — UI Interaction Spec (HARD GATE for Phase 2)
    │
    ▼
T0 COMPLETE + T1.7 LOCKED → Phase 2 opens
    │
    ├── T2.2  Async handoff
    ├── T2.3  SSE + directives + caching (largest, unblocks Phase 3)
    ├── T2.4  Belief slugs
    ├── T2.5  Belief history
    ├── T2.6  Signals table + dual-write hook
    ├── T2.7  Entities RPC
    └── T2.8  Schema reference doc (LAST)
    │
    ▼
PHASE 2 COMPLETE → Phase 3 (Maxwell clears each)
    │
    ├── T3.1  Response parser (after T2.3)
    ├── T3.2  Directive handler (after T2.3)
    ├── T3.3  Supabase integration (after T2.4-T2.7)
    ├── T3.4  Runtime integration (after T0 + T2.3)
    └── T3.5  Launch validation (after all)
```

---

## STOP Gate Tiers

| Tier | When | Tasks |
|---|---|---|
| **Full STOP** (Architect + Max review) | Architectural or high-risk | T0.1, T0.3, T2.3, T2.6, T3.3, T3.4, T3.5 |
| **Batch-merge** (`[BATCH]` in title, Max reviews in batch) | Mechanical, low regression risk | T1.1-T1.4, T1.5a, T1.5b, T1.6, T2.4, T2.5, T2.7, T2.8, T3.1, T3.2 |
| Tier decided at PR-open time | If a batch PR discovers unexpected complexity, escalate to full STOP | Any |

---

## Migration Tooling

Schema migrations use `supabase/migrations/` with numbered SQL files (existing pattern from Stage 0). Application method: `supabase db push` if CLI is configured, or manual paste into Supabase SQL Editor. First T0/T2 PR that adds a migration documents which method was used — all subsequent PRs follow.

Every PR that creates a new table includes a **Maxwell post-merge checklist** in the PR description:
- [ ] Enable RLS on new table
- [ ] Enable Realtime on new table
- [ ] Verify with a test query
