# Tier Protocol

Canonical reference for all Hammerfall agents. All agent contracts reference this file.

The tier controls proactivity and presence — not agent existence. All cognitive
subsystems exist at every tier. What changes is when they fire and how often Helm
initiates.

Active tier is a config value in `hammerfall-config.md`. Maxwell is sole user at Tier 1.
The lever is an app permission in Quartermaster when productized.

---

## T1 — On-Demand

**TRIGGER:** User engages the app.

**AGENTS:** All cognitive subsystems run per-turn within session. Reactive only. No
autonomous initiation between sessions.

**HARDWARE:** Any capable LLM with tool-use. Claude Code is the current implementation.
Model-agnostic by design — agent contracts define interfaces, not model implementations.

**T1 Enforcement Note:**
At T1, agent separation is enforced by prompt discipline within a single session context.
The NEVER constraints in each agent contract are behavioral roles, not process boundaries.
At T3, physical process isolation enforces the same contracts. The behavioral contract
is identical at both tiers. This is explicitly acknowledged in every agent file — it is
not a gap, it is T1 reality.

---

## T2 — Scheduled

**TRIGGER:** User-set cadence (cron or equivalent).

**AGENTS:**
- Helm Prime initiates on schedule
- Projectionist pre-loads context from prior session frames
- Archivist batches pending writes

**HARDWARE:** T1 hardware plus a persistent scheduler. No new inference hardware required.

---

## T3 — Ambient

**TRIGGER:** Always on — event-driven continuous operation.

**AGENTS:** Full physical separation. Each agent is a persistent process.
- Helm Prime + Projectionist + Archivist → DGX Spark
- Communication via message bus (Redis or equivalent)

**HARDWARE:** DGX Spark. Single-node architecture.

**T3 Note:** The behavioral contracts written at T1 are validated by months of real
sessions before Stage 4 hardware arrives. Nothing gets thrown away. BA7 (orchestration
layer) wires smaller Ollama models to Projectionist and Archivist roles as a T3 proving
ground before the Spark ships.

---

## Config Values (hammerfall-config.md)

```yaml
active_tier: T1
frame_offload_interval: 10        # Interval trigger: every N turns
warm_queue_max_frames: 20         # Batch trigger: fires at exactly this count
frame_offload_conservative: true  # Interval fires at 80% of interval when true
```

These values are read by the Projectionist at session start.

---

## Agent Hardware Assignment by Tier

| Agent | T1 | T2 | T3 |
|---|---|---|---|
| Helm Prime | Claude Code | Claude Code | DGX Spark |
| Projectionist | Claude Code (Agent tool) | Claude Code (Agent tool) | DGX Spark |
| Archivist | Claude Code (Agent tool) | Claude Code (Agent tool) | DGX Spark |

## Taskers — Stage 4 Forward Reference

Taskers are scope-bound Helm instances created dynamically by Helm Prime at Stage 4.
Each Tasker is a full Helm stack (Helm Prime + Projectionist + Archivist) operating
within a bounded project or task context. All Taskers write to the same Supabase brain
scoped
by `project` and `agent` fields. One identity, one brain. Helm Prime creates and prunes
Taskers as work starts and ends. The IDE Helm is a manually-created example of what a
Tasker will look like when the pattern is fully operational.

---

*Canonical source: `agents/shared/tier_protocol.md`*
*Maintained by Core Helm. Changes require Maxwell approval.*
