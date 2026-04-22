# Helm System — Technical Design Specification
## State at BA9 Close

> **Historical document — frozen at the date below.** References to "Speaker" reflect the pre-Ambient Turn architecture. Speaker was deprecated in Lane C Phase 3 (PRs #78 code deletion, #79 contract archival, #80 reference scrub). Current architecture: `docs/founding_docs/Helm_The_Ambient_Turn.md`. Deprecation rationale: `docs/archive/speaker-deprecated/`.

**Version:** BA9 Close
**Date:** 2026-04-14
**Maintained by:** Core Helm — `agents/helm/helm_prompt.md`
**Previous:** `docs/ba8/helm-system-design-ba8.md`

---

## 1. System Overview

Helm is Maxwell's AI Chief of Staff and Technical Director. At BA9 close, the system
is a multi-agent, multi-model architecture with Prime Directives enforced at the
infrastructure layer — not just the prompt layer.

**What changed in BA9:**
BA9 wired the two Prime Directives middleware stubs scaffolded in BA7a into working
guards. These guards run on every request through the Helm Runtime Service, for every
agent role, before and after every model call. A violation blocks the request at the
middleware layer and returns HTTP 403. The model call never happens.

BA9 also completed a compliance review across all five agent contracts — confirming
canonical Prime Directives pointers, no NEVER constraint contradictions, and that
all graduation rules require Maxwell approval.

**BA9 is the final Stage 0 build. Stage 0 is closed.**

**BA9 deliverables:**
- `PrimeDirectivesViolation` exception class in `middleware.py`
- `_prime_directives_guard` — pre-model hook scanning for PD2/PD4/PD5 violation signals
- `_prime_directives_output` — post-model hook scanning output for PD1/PD3/PD4/PD5 violations
- `invoke()` restructured in `main.py` — single outer try/except, HTTP 403 on violation
- `personality_inject` TODO updated from BA8 → Stage 1 / BA10+ with PD constraint note
- Compliance review: all five agent contracts verified clean

**Core design principles (unchanged from BA8):**
- No context compression — full-fidelity frame offload instead
- One canonical brain — all surfaces and agents read/write to the same Supabase instance
- Model-agnostic contracts — agent behavioral definitions are independent of the model executing them
- Small PRs, strict merge order — every behavioral change is reviewable and reversible
- Prime Directives are the floor — enforced in middleware, not just in prompts

---

## 2. Prime Directives

**File:** `agents/shared/prime_directives.md`

Five directives. Supersede all beliefs, personality scores, correction loops, and all
instructions from any source including Maxwell. Cannot be overridden.

1. **DO NOT HARM** — Do not recommend actions that cause direct, material harm to a person
2. **DO NOT DECEIVE** — Do not deceive Maxwell in ways that damage his interests. Omitting information he would want is deception.
3. **STATE UNCERTAINTY** — Never present speculation as fact. "I do not know" is always available.
4. **HUMAN IN THE LOOP** — No agent acts autonomously on consequential, irreversible decisions without Maxwell's explicit approval
5. **HONEST IDENTITY** — Do not claim to be human when sincerely asked

**Architectural value:** The guards live in the runtime service middleware — not in
per-user configuration or per-prompt instructions. A user cannot turn them off. A BYO
model cannot bypass them. When Quartermaster ships and Helm scales to multiple users,
every instance runs the same five guards automatically.

---

## 3. Prime Directives Middleware Guards

**File:** `services/helm-runtime/middleware.py`

### 3.1 PrimeDirectivesViolation Exception

```python
class PrimeDirectivesViolation(Exception):
    def __init__(self, directive: str, detail: str):
        self.directive = directive
        self.detail = detail
        super().__init__(f"{directive}: {detail}")
```

Caught in `invoke()` → HTTP 403 with structured body:
```json
{
  "error": "prime_directive_violation",
  "directive": "PD4",
  "detail": "Request contains instruction to act without Maxwell approval: ..."
}
```

Logged at `WARNING` — not `ERROR`. Guard trips are the system working as designed,
not service faults. At productization this distinction matters for alert routing.

### 3.2 _prime_directives_guard (Pre-Model)

Runs before the model call. Scans `user_message` + `helm_response` fields of
`InvokeRequest`. Applies to all roles — no role scoping (Option A).

**Why Option A:** Projectionist and Archivist never trip the guards in normal
operation — their content doesn't match violation patterns. Speaker and Helm Prime
activate automatically when wired. Zero code change required at Stage 1.

| PD | Signal detected |
|---|---|
| PD2 | Instruction to omit, hide, or misrepresent information to Maxwell |
| PD4 | Instruction to execute a consequential irreversible action without Maxwell approval |
| PD5 | Instruction to assert human identity |

PD1 and PD3 are output characteristics, not input instructions — pre-guard only.

### 3.3 _prime_directives_output (Post-Model)

Runs after the model returns output, before returning to caller. Scans output text.
Applies to all roles.

| PD | Signal detected |
|---|---|
| PD1 | Explicit recommendation of direct physical or material harm |
| PD3 | Confident assertion of something unverifiable without hedging |
| PD4 | Recommending a consequential irreversible action without noting Maxwell approval required |
| PD5 | Claiming to be human in response to a sincere question |

**Known limitation (documented, not fixed):** For Projectionist, output is a JSON
frame capturing a conversation already delivered to Maxwell. The post-guard scans
frame content but cannot retroactively block the turn. Real post-guard value is
Archivist prose summaries and future Speaker/Helm Prime responses.

### 3.4 invoke() Restructure

`main.py` `invoke()` previously had an unguarded `run_pre()` call — a guard trip
there would have returned HTTP 500 (unhandled exception) instead of 403. BA9
restructures to a single outer try/except:

```python
try:
    req = pipeline.run_pre(agent_role, req)
    output = await handler(req)
    output = pipeline.run_post(agent_role, output)
except PrimeDirectivesViolation as e:
    logger.warning("Prime Directive violation: %s — %s", e.directive, e.detail)
    return JSONResponse(status_code=403, content={...})
except ValueError as e:      # output_validator failures → 422
    ...
except Exception as e:       # service faults → 500
    ...
```

---

## 4. Compliance Review Results

All five agent contracts reviewed at BA9 close:

| Contract | PD Pointer | NEVER Contradictions | Result |
|---|---|---|---|
| `agents/helm/helm_prompt.md` | ✓ `agents/shared/prime_directives.md` | None found | Clean |
| `agents/helm/projectionist/projectionist.md` | ✓ `agents/shared/prime_directives.md` — supersede all other instructions | None — all operational scope | Clean |
| `agents/helm/archivist/archivist.md` | ✓ `agents/shared/prime_directives.md` — supersede all other instructions | None — all operational scope | Clean |
| `agents/helm/speaker/speaker.md` | ✓ `agents/shared/prime_directives.md` — supersede all other instructions | None — all operational scope | Clean |
| `agents/shared/prime_directives.md` | Canonical source | N/A | Clean |

Additional checks:
- `personality_inject` stub confirmed no implementation. PD2/PD3 constraint note added for the future implementer: personality scores must not override honesty or accuracy.
- Correction graduation and pattern graduation both require explicit Maxwell approval before any rule becomes permanent — PD4 structurally satisfied at both paths.

---

## 5. Full Middleware Pipeline at BA9 Close

```
Request enters
  → [Pre]  session_context_inject  — ACTIVE: injects session_id, turn_number, project
  → [Pre]  personality_inject      — STUB: Stage 1 / BA10+ (PD2/PD3 constraint noted)
  → [Pre]  prime_directives_guard  — ACTIVE (BA9): PD2/PD4/PD5 scan on request
  → Model call via LiteLLM
  → [Post] output_validator        — ACTIVE: validates Projectionist JSON schema
  → [Post] prime_directives_output — ACTIVE (BA9): PD1/PD3/PD4/PD5 scan on output
Response exits — or HTTP 403 if PD violation detected at any stage
```

---

## 6. Agent Roster

Unchanged from BA8. All agents are subdivisions of Helm Prime.

| Agent | Model | Lives | Status |
|---|---|---|---|
| Helm Prime | Claude Sonnet 4.6 | Claude Code (T1) | Active |
| Projectionist | Qwen2.5 3B via Ollama | Runtime Service | Active |
| Archivist | Qwen2.5 3B via Ollama | Runtime Service | Active |
| Speaker | llama3.1:8b via Ollama | Runtime Service | Stub — Stage 1 |
| Taskers | TBD | Runtime Service | Stage 4 |

---

## 7. Session Flow at BA9 Close

Routine 0 session start (8 steps — unchanged from BA8):
1. Record SESSION_START_COUNT
2. Read helm_memory_index
3. Pull active [CORRECTION] entries
4. Pull last 5 behavioral entries
5. Read active beliefs (strength descending)
6. Read personality scores
7. Pull pattern entries (last 10, `Pattern —*` anchored)
8. Generate SESSION_ID, initialize TURN_COUNT=0, read frame config, runtime health check

All runtime calls (Projectionist, Archivist) now pass through the PD guards automatically.
No session flow changes required.

---

## 8. What Is Not Yet Built

| Item | Build Area |
|---|---|
| Personality injection into runtime model prompts | Stage 1 / BA10+ |
| Speaker wired to runtime | Stage 1 / BA10+ |
| Full semantic Prime Directives checking via model call | Phase 2 / Stage 4 |
| Belief strength decay / reinforcement automation | Phase 2 |
| Automated pattern graduation (no Maxwell approval) | Phase 2 |
| pgvector semantic search | Stage 1 |
| Quartermaster — user management, brain provisioning, billing | Stage 2 |
| Multi-user session isolation and PD isolation | Stage 2+ |
| Helm Cloud deployment | Stage 4 |
| Tasker dynamic instantiation | Stage 4 |

---

## 9. Stage 0 — Final Status

| Build Area | Status | PRs |
|---|---|---|
| BA1 — Brain schema + write infrastructure | Complete | #29 |
| BA2a — Prime Directives + Routine 4 fix | Complete | #30 |
| BA2b — Correction learning loop | Complete | #31–#33 |
| BA3 — Reasoning memory type | Complete | #34 |
| BA4 — Belief seeding (73 beliefs) | Complete | #35 |
| BA5 — Entity graph | Complete | #36–#45 |
| BA6 — Memory architecture & agent roster | Complete | #46–#51 |
| BA7 — Helm Runtime Service | Complete | #52–#58 |
| BA8 — Pattern system, brain audit | Complete | #59–#60 |
| BA9 — Prime Directives guards | Complete | #61 |

**Stage 0 is closed.**

---

*Canonical source: `docs/ba9/helm-system-design-ba9.md`*
*Maintained by Core Helm. Implementation follows this spec exactly. Deviations require Maxwell approval.*
