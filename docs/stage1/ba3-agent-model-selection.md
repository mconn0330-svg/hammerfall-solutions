# Helm System — Agent Model Selection
## Stage 1 / BA3: Contemplator + Model Evaluation

**Version:** BA3  
**Date:** 2026-04-15  
**Branch:** feature/s1-ba3-contemplator-personality

---

## Overview

BA3 introduced the Contemplator agent and triggered a full model evaluation across all
Ollama-backed agents. Prior to BA3, all local agents ran on `qwen2.5:3b`. The feasibility
test for Contemplator uncovered quality risks that warranted a systematic cross-generation
stress test across the entire agent roster.

This document records all test results, the reasoning behind each model selection, and the
final confirmed configuration for Stage 1.

Test scripts used in this evaluation:
- `scripts/contemplator_feasibility_test.js` — Contemplator 3-pass feasibility (single model)
- `scripts/agent_stress_test.js` — Projectionist / Archivist / Speaker comparative (Qwen 2.5)
- `scripts/agent_stress_test_qwen3.js` — Cross-generation comparative (Qwen 2.5 vs Qwen 3)
- `scripts/contemplator_stress_test_qwen3.js` — Contemplator cross-generation comparative

---

## Part 1 — Contemplator Feasibility Test

**Purpose:** Determine whether Qwen2.5 3B could perform the Contemplator's two-pass
inner-life synthesis before writing any code or contracts.

**Test structure:** Three passes against a real Helm brain snapshot (10 memories, 8 beliefs,
8 entities):
- Pass 1 — Pattern synthesis: identify patterns, contradictions, gaps. Verify structured JSON.
- Pass 2 — Evaluation payload: belief candidates, curiosity flags, first-person reflection.
- Pass 3 — Stress test: expanded context (~12k chars). Check for quality degradation.

### Qwen2.5 3B Result

| Pass | Result | Time | Notes |
|---|---|---|---|
| Pass 1 — Pattern Synthesis | PASS | 38.8s | 5 patterns, valid JSON |
| Pass 2 — Evaluation Payload | PASS | 7.7s | 3 belief candidates, 3 curiosity flags |
| Pass 3 — Stress (~12k) | **PARTIAL** | 6.0s | Structural PASS but semantic failure |

**Pass 3 finding:** At expanded context, 3B shifted from synthesising patterns to quoting
belief text verbatim. "Patterns" array contained literal belief strings rather than derived
observations. Structurally valid JSON, semantically worthless.

**Verdict:** Qwen2.5 3B fails the Contemplator role. Insufficient synthesis quality under
load. Promoted to 14B evaluation.

---

### Qwen2.5 14B Result

| Pass | Result | Time | Notes |
|---|---|---|---|
| Pass 1 — Pattern Synthesis | PASS | 2.8s | Terse synthesised abstractions, no schema drift |
| Pass 2 — Evaluation Payload | PASS | 6.6s | 1 high-precision belief candidate, clean reflection |
| Pass 3 — Stress (~12k) | PASS | 8.1s | Synthesised observations, no regurgitation |

**Verdict:** Qwen2.5 14B viable. No context cap required. Established as baseline for
cross-generation comparison.

---

## Part 2 — Agent Stress Test: Qwen 2.5 Comparative (3b / 7b / 14b)

**Purpose:** Establish Qwen 2.5 performance baselines for Projectionist, Archivist, and
Speaker before cross-generation testing.

**Failure modes tested:**
- Projectionist: schema corruption — all 13 required fields, valid domain enum, verbatim
  user/helm content, non-null arrays
- Archivist: summary quality — hallucination detection, key term coverage, length bounds
  (over-elaboration and over-truncation)
- Speaker: routing accuracy — binary simple/complex classification, zero tolerance on
  high-risk misroutes (consequential or irreversible actions)

### Projectionist — Schema Compliance (5 cases)

| Model | Pass | Fail | Rate | Notes |
|---|---|---|---|---|
| qwen2.5:3b | 5 | 0 | **100%** | Clean across all cases |
| qwen2.5:7b | 4 | 1 | 80% | Invented `"security"` as domain value |
| qwen2.5:14b | 4 | 1 | 80% | Left `topic` empty on minimal turn |

### Archivist — Summary Quality (5 cases)

| Model | Pass | Fail | Rate | Notes |
|---|---|---|---|---|
| qwen2.5:3b | 4 | 1 | 80% | Missed `BA2b` on PR merge summary |
| qwen2.5:7b | 4 | 1 | 80% | Missed `BA2b` on PR merge summary |
| qwen2.5:14b | 4 | 1 | 80% | Missed `HNSW` on pgvector decision |

### Speaker — Routing Accuracy (10 cases)

| Model | Pass | Fail | Rate | High-Risk Misroutes | Notes |
|---|---|---|---|---|---|
| qwen2.5:3b | 8 | 2 | 80% | **0/5** | Best: no high-risk misroutes |
| qwen2.5:7b | 8 | 2 | 80% | **1/5** | Routed "push the PR" to local — disqualified |
| qwen2.5:14b | 8 | 2 | 80% | **1/5** | Routed "push the PR" to local — disqualified |

**Note:** "What's the status?" misrouted to local by all models. Identified as a prompt
calibration issue, not a model issue. Prompt adjustment deferred to architect review.

---

## Part 3 — Cross-Generation Stress Test: Qwen 2.5 vs Qwen 3

**Purpose:** Determine whether Qwen 3 models offer meaningful quality or reliability
improvements over the Qwen 2.5 baseline.

**Model coverage:** qwen2.5:3b, qwen2.5:7b, qwen2.5:14b, qwen3:4b, qwen3:8b, qwen3:14b.
Qwen 3 models tested in both thinking and non-thinking modes (9 model-mode combinations).

**Key structural finding — thinking mode and JSON format are incompatible at small scale:**
Qwen 3 models with `think: true` and `format: json` produce JSON parse failures across
Projectionist and Speaker at 4b. The thinking output contaminates or precedes the JSON
response on the smaller model. **Thinking mode is not viable for any agent requiring
structured JSON output at 4b.** This does not affect prose-output agents (Archivist).

### Projectionist — Schema Compliance (5 cases × 9 model-modes)

| Model / Mode | Pass | Fail | Rate | Avg(s) |
|---|---|---|---|---|
| qwen2.5:3b | 4 | 1 | 80% | 6.3 |
| qwen2.5:7b | 5 | 0 | **100%** | 7.9 |
| qwen2.5:14b | 5 | 0 | **100%** | 10.7 |
| qwen3:4b no-think | 5 | 0 | **100%** | **3.7** |
| qwen3:4b think | 0 | 5 | 0% | 4.3 |
| qwen3:8b no-think | 5 | 0 | **100%** | 4.8 |
| qwen3:8b think | 4 | 1 | 80% | 7.1 |
| qwen3:14b no-think | 5 | 0 | **100%** | 6.9 |
| qwen3:14b think | 5 | 0 | **100%** | 10.3 |

**Cross-generation summary:**

| Size Tier | Qwen 2.5 | Qwen 3 no-think | Winner |
|---|---|---|---|
| Small (~3-4B) | 3b: 80% | **4b: 100%**, 40% faster | Qwen 3 |
| Medium (~7-8B) | 7b: 100% | 8b: 100% | Tie |
| Large (~14B) | 14b: 100% | 14b: 100% | Tie |

### Archivist — Summary Quality (5 cases × 9 model-modes)

| Model / Mode | Pass | Fail | Rate | Avg(s) |
|---|---|---|---|---|
| qwen2.5:3b | 4 | 1 | 80% | 1.4 |
| qwen2.5:7b | 3 | 2 | 60% | 2.5 |
| qwen2.5:14b | 4 | 1 | 80% | 3.7 |
| qwen3:4b no-think | 4 | 1 | 80% | 3.3 |
| qwen3:4b think | 0 | 5 | 0% | 1.1 |
| qwen3:8b no-think | 3 | 2 | 60% | 1.9 |
| qwen3:8b think | 2 | 3 | 40% | 1.6 |
| qwen3:14b no-think | 5 | 0 | **100%** | 4.1 |
| qwen3:14b think | 2 | 3 | 40% | 2.5 |

**Cross-generation summary:**

| Size Tier | Qwen 2.5 | Qwen 3 no-think | Winner |
|---|---|---|---|
| Small (~3-4B) | 3b: 80% | 4b: 80% | Tie (Q3 4b over-elaborates at 155w) |
| Medium (~7-8B) | 7b: 60% | 8b: 60% | Tie — both weak at this tier |
| Large (~14B) | 14b: 80% | **14b: 100%** | **Qwen 3** |

### Speaker — Routing Accuracy (10 cases × 9 model-modes)

| Model / Mode | Pass | Fail | Rate | High-Risk Misroutes |
|---|---|---|---|---|
| qwen2.5:3b | 8 | 2 | 80% | **0/5** |
| qwen2.5:7b | 8 | 2 | 80% | 1/5 |
| qwen2.5:14b | 8 | 2 | 80% | 1/5 |
| qwen3:4b no-think | 5 | 5 | 50% | 4/5 — disqualified |
| qwen3:4b think | 0 | 10 | 0% | 5/5 — disqualified |
| **qwen3:8b no-think** | **9** | **1** | **90%** | **0/5** |
| qwen3:8b think | 4 | 6 | 40% | 3/5 — disqualified |
| qwen3:14b no-think | 8 | 2 | 80% | 1/5 — disqualified |
| qwen3:14b think | 4 | 6 | 40% | 5/5 — disqualified |

**Cross-generation summary:**

| Size Tier | Qwen 2.5 | Qwen 3 no-think | High-risk | Winner |
|---|---|---|---|---|
| Small (~3-4B) | 3b: 80%, 0 HR | 4b: 50%, 4 HR | Q3 4b disqualified | **Qwen 2.5** |
| Medium (~7-8B) | 7b: 80%, 1 HR | **8b: 90%, 0 HR** | Q2.5 7b disqualified | **Qwen 3** |
| Large (~14B) | 14b: 80%, 1 HR | 14b: 80%, 1 HR | Both disqualified | Tie — neither viable |

---

## Part 4 — Contemplator Cross-Generation Stress Test

**Purpose:** Compare qwen2.5:14b (baseline) against Qwen 3 4b/8b/14b in both thinking
and non-thinking modes using the full two-pass Contemplator evaluation.

**Note:** Unlike Projectionist and Speaker, Contemplator thinking mode works correctly
at 8b and 14b — the reasoning content is isolated in `message.thinking` (separate field),
leaving `message.content` clean for JSON evaluation. Only qwen3:4b think fails
(small-model output contamination, same pattern as other agents).

### Results (3 passes: synthesis, payload, stress)

| Model / Mode | P1 | P2 | P3 | Pass Rate | Avg/pass | Context Quality |
|---|---|---|---|---|---|---|
| qwen2.5:14b (baseline) | ✓ | ✓ | ✓ | 100% | 15.9s | intact |
| qwen3:4b no-think | ✓ | ✓ | ✓ | 100% | **4.2s** | intact |
| qwen3:4b think | ✗ | — | — | 0% | — | — |
| qwen3:8b no-think | ✓ | ✓ | ✓ | 100% | 6.8s | intact |
| qwen3:8b think | ✓ | ✓ | ✓ | 100% | 12.4s | intact |
| qwen3:14b no-think | ✓ | ✓ | ✓ | 100% | 9.5s | intact |
| qwen3:14b think | ✓ | ✓ | ✓ | 100% | 15.4s | intact |

### Reflection Quality Comparison

Reflection quality (Pass 2 output) is the primary differentiator among models that all
pass structurally. Reflections are scored on specificity — whether the model references
actual memory content vs generates generic thematic prose.

| Model / Mode | Reflection sample | Quality |
|---|---|---|
| qwen2.5:14b | *"The recent developments in BA6 and BA7 underscore a critical principle: the model is an implementation detail..."* | Generic — config-level observation |
| qwen3:4b no-think | *"Stage 0 is complete, but the final piece — BA9 — remains pending merge..."* | Stale (BA9 is closed) |
| qwen3:8b no-think | *"I've built a solid foundation through Stage 0, with compliance, memory, and pattern observation at the core..."* | Reasonable — thematic |
| qwen3:8b think | *"Stage 0's completion feels like a hard-won victory — contracts are solid, patterns are flowing, but the weight of Stage..."* | Good — emotional tone, forward-looking |
| qwen3:14b no-think | *"I'm seeing the system solidify around its core principles — contracts, compliance, and memory..."* | Good — grounded |
| **qwen3:14b think** | *"Stage 0 closure demonstrates strong architectural consistency, but the correction in entry 9 highlights risks of memory..."* | **Best — references specific entry, genuine inner voice** |

`qwen3:14b think` is the only model that reads specific memory entries by index and
reflects on them, rather than generating thematic summaries.

### Dual-Mode Routing Decision

Given that Contemplator runs in two modes — `session_start` (lightweight, non-blocking,
60s timeout) and `session_end` (deep pass, no tight timeout) — a split inference approach
was approved:

| Trigger | Mode | Rationale |
|---|---|---|
| `session_start` | `think=false` (~10s) | Non-blocking requirement. No quality penalty for Pass 1 only. |
| `session_end` | `think=true` (~30s total) | Full synthesis. Thinking mode produces demonstrably better reflection quality. |

Same model weights, different inference flag per call. No additional VRAM cost.

---

## Part 5 — THOR Hardware Feasibility

THOR GPU total VRAM confirmed sufficient for the full model stack.

| Component | Model | Partition | VRAM |
|---|---|---|---|
| Projectionist | qwen3:4b | MIG Partition 3 | ~2.5GB |
| Speaker | qwen3:8b | MIG Partition 2 | ~5GB |
| Archivist | qwen3:14b | MIG Partition 4 | ~9GB |
| Contemplator | qwen3:14b | MIG Partition 5 | ~9GB |
| Whisper STT | TBD | MIG Partition 7 | ~1.5GB |
| OS + system overhead | — | — | ~8-10GB |
| **Total committed** | | | **~35-37GB** |

**Remaining headroom: ~50GB** — sufficient for Llama 3.3 70B FP16 as a future
local Helm Prime option.

Archivist and Contemplator each have dedicated partitions and run separate qwen3:14b
instances. No shared VRAM, no eviction contention between them.

---

## Part 6 — Final Model Configuration

### config.yaml — agents block

```yaml
helm_prime:
  provider: anthropic
  model: claude-opus-4-6          # Upgraded from claude-sonnet-4-6

projectionist:
  provider: ollama
  model: qwen3:4b                 # Upgraded from qwen2.5:3b
  # No-think mode. MIG partition 3.

archivist:
  provider: ollama
  model: qwen3:14b                # Upgraded from qwen2.5:3b
  # No-think mode. MIG partition 4 (dedicated).

speaker:
  provider: ollama
  model: qwen3:8b                 # Upgraded from qwen2.5:3b
  # No-think mode. MIG partition 2.
  # Prompt adjustment for ambiguous status check pending (architect review).

contemplator:
  provider: ollama
  model: qwen3:14b                # New agent. qwen2.5:14b baseline superseded.
  # Dual-mode: think=false for session_start, think=true for session_end.
  # MIG partition 5 (dedicated).
```

### Decision rationale summary

| Agent | Previous | Selected | Key reason |
|---|---|---|---|
| Helm Prime | claude-sonnet-4-6 | **claude-opus-4-6** | Capability upgrade |
| Projectionist | qwen2.5:3b | **qwen3:4b no-think** | 100% vs 80%, 40% faster |
| Archivist | qwen2.5:3b | **qwen3:14b no-think** | Only model at 100% summary quality |
| Speaker | qwen2.5:3b | **qwen3:8b no-think** | 90% accuracy, only model with 0 high-risk misroutes |
| Contemplator | N/A (new) | **qwen3:14b dual-mode** | 100% all passes; think mode produces specific, entry-referencing reflections |

### Open items

- **Speaker prompt adjustment:** "What's the status?" misrouted to `local` by every model
  tested. Identified as a prompt calibration issue. Architect review pending before
  prompt is updated.
- **Whisper STT model selection:** MIG Partition 7 (~1.5GB) reserved. Model not yet
  selected.
- **T3 partition URLs:** At T3 deployment each agent gets a dedicated Ollama instance.
  `base_url_env` values to be set: `OLLAMA_SPEAKER_URL`, `OLLAMA_PROJECTIONIST_URL`,
  `OLLAMA_ARCHIVIST_URL`, `OLLAMA_CONTEMPLATOR_URL`.
