# BA3 Close — Contemplator + Personality Injection
## Stage 1 Build Area 3

**Status:** CLOSED  
**PR:** #66 (merged)  
**Branch:** feature/s1-ba3-contemplator-personality  
**Date closed:** 2026-04-15  

---

## What BA3 Is

BA3 is the most important build in Stage 1. Projectionist and Archivist gave Helm memory.
Contemplator gives Helm a mind.

The difference between a reactive tool and an ambient intelligence is whether something
happens when Maxwell is not talking to it. BA3 is what makes things happen.

BA3 delivered:
1. **Contemplator** — Helm's inner life. Belief evaluation, pattern synthesis, curiosity
   flagging, reflection monologue. Runs at session start and session end without Maxwell
   commanding it.
2. **Full agent model upgrade** — All Ollama-backed agents upgraded from Qwen 2.5 3B to
   Qwen 3 variants, determined by a systematic cross-generation stress test.
3. **Personality injection** — Helm Prime's voice is now consistent whether invoked via the
   runtime or directly in Claude Code.
4. **BA2 gap closure** — Routine 6 semantic search (match_memories RPC) wired as primary;
   ILIKE retained as fallback.

---

## Architecture Decisions

### Decision 1 — Contemplator as a subdivision, not a protocol

Contemplator follows the same pattern as Projectionist and Archivist: a dedicated agent
with a single well-defined job. It is not a script, not a cron job, not an instruction to
Helm Prime. It is its own handler in the runtime, invoked via `/invoke/contemplator`.

This decision keeps the architecture clean. Contemplator has a behavioral contract, an
NEVER constraints list, and a write protocol — the same level of formal definition as
every other agent in the system.

### Decision 2 — Two-pass execution design

Contemplator runs in two passes to separate data gathering from evaluation:

- **Pass 1 (data gathering):** Read brain snapshot, identify candidates for belief evaluation,
  pattern synthesis, curiosity flagging. Produce structured candidate list. Pattern matching
  and retrieval only — no evaluation.
- **Pass 2 (evaluation + write payload):** Reason over the candidate list, produce structured
  JSON payload with belief patches, pattern entries, curiosity flags, and reflection.

This separation prevents a single long reasoning pass from conflating retrieval quality with
evaluation quality. It also enables session_start to run Pass 1 only (fast, non-blocking)
and session_end to run both passes (full synthesis).

### Decision 3 — Dual-mode think routing on qwen3:14b

Rather than two separate models (one for lightweight, one for deep), Contemplator uses a
single `qwen3:14b` instance with the `think` parameter toggled per trigger:

- `session_start`: `think=false` — Pass 1 only, ~10s, non-blocking
- `session_end`: `think=true` — Pass 1 + Pass 2, ~30s, full synthesis quality

The model weights are identical. No additional VRAM. The `think` flag changes inference
behavior, not model identity. qwen3:14b with think=true was the only model that referenced
specific memory entries by index in reflections — qualitatively the best output across all
tested combinations.

THOR feasibility confirmed by architect: Contemplator gets dedicated MIG partition 5 (~9GB),
separate from Archivist on partition 4. No contention, no eviction risk.

See: `docs/stage1/ba3-agent-model-selection.md` for full cross-generation test results.

### Decision 4 — Write protocol via Archivist handoff

Contemplator never writes to Supabase directly. It produces a structured JSON payload and
delivers it to Archivist via `POST /invoke/archivist` with a `contemplator_writes` context
field. Archivist executes each write sequentially.

Rationale: inline writes during reasoning create race conditions. Archivist is the single
write authority for the brain — same constraint as every other agent. Archivist's existing
write path (supabase_client.py) already has retry logic, error handling, and embedding
generation. Reusing it is strictly better than duplicating it.

The handoff is orchestrated in `main.py`'s `_handle_contemplator()`:
1. Call `contemplator.handle()` — returns payload JSON
2. On `session_end_complete`: construct write request with `contemplator_writes` in context
3. Call `archivist.handle()` with that request — Archivist dispatches to
   `_execute_contemplator_writes()` and bypasses the cold frame migration path

### Decision 5 — All Ollama agents upgraded to Qwen 3

The Contemplator feasibility test surfaced a quality risk: Qwen 2.5 3B verbatim-regurgitated
memory entries rather than synthesizing them. That prompted a systematic cross-generation
stress test across all Ollama-backed agents.

Test battery: 9 model-mode combinations per agent — Qwen 2.5 (3b, 7b, 14b) no-think,
Qwen 3 (4b, 8b, 14b) × think/no-think.

Key findings:
- **Thinking mode + JSON format**: incompatible at qwen3:4b (thinking content leaks into
  message.content, breaks JSON parse). Works cleanly at 8b and 14b.
- **High-risk misroute zero tolerance**: Speaker was evaluated with a separate high-risk
  misroute flag. Any model that routed "push the PR" to local was disqualified regardless
  of overall accuracy.
- **Universal Speaker miss**: "What's the status?" was misrouted local by every model at
  every size. Identified as prompt calibration, not model capability. Fixed via architect's
  3-change specification (see Speaker section below).

Final model selection (all confirmed via cross-gen test):

| Agent | Model | Mode | MIG Partition | Rationale |
|---|---|---|---|---|
| Helm Prime | claude-opus-4-6 | API | — | Upgraded from claude-sonnet-4-6 per Maxwell |
| Projectionist | qwen3:4b | no-think | 3 (~2.5GB) | 100% schema compliance vs 80%, 40% faster |
| Archivist | qwen3:14b | no-think | 4 (~9GB) | Only model at 100% summary quality |
| Speaker | qwen3:8b | no-think | 2 (~5GB) | 90% routing accuracy, 0 high-risk misroutes |
| Contemplator | qwen3:14b | dual-mode | 5 (~9GB) | Best reflection specificity (references entries by index) |

Total committed VRAM on THOR: ~35–37GB of ~85GB. ~50GB remaining (supports Llama 3.3 70B FP16).

See: `docs/stage1/ba3-agent-model-selection.md` for full test data, tables, and rationale.

### Decision 6 — Personality injection in speaker.py, not middleware

The `_personality_inject` hook in `middleware.py` has been a stub since BA7. The BA3
decision: implement personality injection directly in `speaker.py` for the Helm Prime
escalation path rather than in the middleware layer.

Rationale: at T1, every user-facing Helm response routes through Speaker. Speaker is the
only runtime path that generates Helm Prime responses. Injecting in `speaker.py` is
targeted and avoids changing the middleware architecture, which would require making
`run_pre()` async.

`_load_personality_block()` loads all `helm_personality` rows from Supabase, formats them
as a concise calibration block (`attribute: score/10 — description`), and appends to the
Helm Prime system prompt. Non-fatal: returns empty string on any failure so the base
identity still produces valid output.

The middleware hook is updated to document this approach and reserve the generalized
hook for T3/BA10+.

---

## Deliverables — Complete Accounting

| Deliverable | File | Status |
|---|---|---|
| Contemplator behavioral contract | `agents/helm/contemplator/contemplator.md` | Done |
| Contemplator agent handler | `services/helm-runtime/agents/contemplator.py` | Done |
| `/invoke/contemplator` endpoint | `services/helm-runtime/main.py` | Done |
| Dual-mode think flag wired | `services/helm-runtime/agents/contemplator.py` | Done |
| Contemplator→Archivist write handoff | `services/helm-runtime/main.py` + `archivist.py` | Done |
| `brain.sh` --patch-id for helm_beliefs | `scripts/brain.sh` | Done |
| Routine 0 — Contemplator session_start (step 9) | `agents/helm/helm_prompt.md` | Done |
| Routine 0 — Contemplator session_end (step 3) | `agents/helm/helm_prompt.md` | Done |
| Routine 0 — [CURIOUS] flag surface instructions | `agents/helm/helm_prompt.md` | Done |
| Routine 6 — semantic search primary (BA2 gap) | `agents/helm/helm_prompt.md` | Done |
| Agent model upgrades — all agents | `services/helm-runtime/config.yaml` | Done |
| Speaker classification prompt hardening | `services/helm-runtime/agents/speaker.py` | Done |
| Personality injection | `services/helm-runtime/agents/speaker.py` | Done |
| middleware.py stub documented | `services/helm-runtime/middleware.py` | Done |
| Feasibility test — Contemplator | `scripts/contemplator_feasibility_test.js` | Done |
| Stress test — Qwen 2.5 baseline | `scripts/agent_stress_test.js` | Done |
| Stress test — Qwen 3 cross-gen | `scripts/agent_stress_test_qwen3.js` | Done |
| Stress test — Contemplator cross-gen | `scripts/contemplator_stress_test_qwen3.js` | Done |
| Agent model selection doc | `docs/stage1/ba3-agent-model-selection.md` | Done |

---

## Speaker Prompt Hardening

Root cause of universal miss: the SIMPLE section included "Status checks that can be answered
without reasoning." Every model read "What's the status?" as a simple status check and routed
it local. There is no named subject — it requires session context — it is a Helm Prime question.

Architect's three-change specification applied:

**Change 1 — Explicit named-subject rule in COMPLEX:**
Any question containing "status", "update", "progress", or "where are we" without a specific
named subject routes to Helm Prime. Named subject distinction: "What is the status of PR #64?"
has a subject. "What's the status?" does not.

**Change 2 — Prior-context-dependency rule in COMPLEX:**
Any question that cannot be answered without knowing what was discussed in the session routes
to Helm Prime. "If you are not certain the question is fully self-contained, route to Helm Prime."

**Change 3 — Explicit AMBIGUOUS section with named examples:**
Added a third category with direct examples: "What's the status?", "Any updates?", "Should
we proceed?", "Are we good?" Explicit examples outperform abstract rules for classification
models — the model matches directly to the example rather than reasoning about prior context.

---

## Curiosity Protocol

Bounded by design. A Helm that surfaces every gap becomes noise.

- Maximum 2 curiosity surfaces per session
- Session_start only — never mid-session
- Priority order: unresolved contradictions → partial entities → thin beliefs → [NOVEL]
- Contemplator flags; Helm Prime voices them in Routine 0 step 9
- At T3 (BA9+): Contemplator can direct Speaker to autonomously seek context via Calendar,
  GitHub, or search — read-only only, per NEVER constraint #1

---

## NEVER Constraints (Contemplator)

1. Read-only external access only. Any write, send, or external state change requires Maxwell explicitly in the loop.
2. Maximum 2 curiosity surfaces per session.
3. Never interrupt Maxwell mid-session.
4. Never declare a belief false — can reduce strength to 0.0, cannot delete or flag false.
5. Never write directly to the brain — all writes via Archivist payload.
6. Never perform strategic reasoning — that is Helm Prime.
7. Never manage frames — that is Projectionist.

---

## Agent Collaboration Chain (complete as of BA3)

```
Session start
  └─ Routine 0 steps 1–8: brain read, beliefs, personality, patterns, Projectionist init
  └─ Routine 0 step 9: Contemplator session_start
       └─ Pass 1 only, think=false, 60s max
       └─ Returns curiosity_flags → surfaced by Helm Prime in first response

Every Maxwell message
  └─ Helm Prime reasons and responds
  └─ Projectionist frames the turn (warm queue)
  └─ Batch trigger: warm queue ≥ WARM_QUEUE_MAX → cold → Archivist drain

Session end
  └─ Step 1: Projectionist resolution pass (canonical/superseded)
  └─ Step 2: Archivist final drain (all cold frames → helm_memory)
  └─ Step 3: Contemplator session_end
       └─ Pass 1 + Pass 2, think=true, ~30s
       └─ Payload: belief patches, pattern entries, curiosity flags, reflection
       └─ main.py hands payload to Archivist → _execute_contemplator_writes()
            └─ PATCH helm_beliefs strength (clamped 0.0–1.0)
            └─ INSERT helm_memory pattern entries (source: contemplator)
            └─ INSERT helm_memory curiosity_flag entries
            └─ INSERT helm_memory monologue entry
```

Speaker sits outside this chain — it classifies every incoming message before the above
loop begins. Simple → local resolution (qwen3:8b answers directly). Complex/ambiguous →
Helm Prime escalation with personality injected.

---

## T1 → T3 Promotion Path

| Component | T1 State | T3 State (BA9) |
|---|---|---|
| Contemplator trigger | Session start + session end (Maxwell-triggered) | Scheduled daemon on MIG partition 5 |
| Contemplator Ollama instance | Shared OLLAMA_BASE_URL | Dedicated `OLLAMA_CONTEMPLATOR_URL` (partition 5) |
| Archivist Ollama instance | Shared OLLAMA_BASE_URL | Dedicated `OLLAMA_ARCHIVIST_URL` (partition 4) |
| Speaker personality | Loaded per-request from Supabase | Loaded at Speaker session init (persistent process) |
| Routine 0 step 9 | Interactive bash block | Speaker session init reads brain at T3 startup |

Config swap is one line per agent in `config.yaml` — `base_url_env` switches from
`OLLAMA_BASE_URL` to the dedicated partition env var. No code changes required.

---

## Open Items Carried Forward

| Item | BA | Notes |
|---|---|---|
| Speaker prompt re-test | BA4/BA5 | Re-run "What's the status?" test case with updated prompt to confirm fix before BA5 E2E |
| Speaker session initialization at T3 | BA9 | Persistent process must load helm_personality and helm_beliefs at startup (Section 17 from BA7 spec) |
| Contemplator promoted to daemon | BA9 | Scheduled daemon on permanent MIG partition 5 |
| Personality injection generalized | BA10+ | Middleware hook (_personality_inject) reserved for T3 generalized implementation |
