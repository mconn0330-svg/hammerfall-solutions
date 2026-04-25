# Helm Productization Path

**Document status:** Internal reference  
**Classification:** Hammerfall Solutions — internal  
**Relates to:** `helm-vision-v1.md`, `Appendix A2 — Technical Shape`  
**Last updated:** April 2026

---

## Overview

This document maps Helm's infrastructure evolution from Maxwell's personal instance to a multi-user product. It covers four distinct tiers — T1 through T3 for the personal instance, and Productization as a separate infrastructure build layered on top.

The architecture is additive by design. Each tier extends the previous one without requiring a rebuild. The personal instance at T3 is the proof-of-concept for productization. Nothing gets thrown away.

---

## Tier Summary

| Tier | Hardware | Prime | Contemplator | Mobile path | Cost model |
|------|----------|-------|--------------|-------------|------------|
| T1 | 4090 workstation | Anthropic API (Opus) | Per-session only | Render → Anthropic API | API tokens |
| T2 | 4090 workstation | Anthropic API (Opus) | Scheduled cron | Render → Anthropic API | API tokens |
| T3 | NVIDIA Thor | Claude Max SDK or local 70B | Always-on process | Render → Thor runtime | Subscription flat |
| Prod | GPU cluster (cloud) | Shared 70B pool | Per-user job queue | API gateway → cluster | Per-user SaaS |

---

## T1 — Local On-Demand (Current State)

### What it is
Everything runs on Maxwell's local workstation. Helm responds when invoked. No persistent background processes. Contemplator fires within sessions only.

### Infrastructure
- **Compute:** RTX 4090 workstation (24GB VRAM)
- **Inference:** Ollama serving Qwen3 4B (Projectionist) and Qwen3 14B (Archivist, Contemplator)
- **Prime:** Anthropic API — Opus-class model via LiteLLM router
- **Brain:** Supabase (hosted, always-on, no maintenance burden)
- **Runtime:** FastAPI at `services/helm-runtime/` — Docker Compose + Ollama sidecar
- **Mobile gateway:** Render — proxies requests to runtime when available, falls back to direct Anthropic API call when local runtime unreachable

### Request flow

```
Desktop:
User → FastAPI (local) → model_router.py → Ollama (local) OR Anthropic API
                                         → Supabase Brain read/write

Mobile:
User → Render → [local runtime unreachable] → Anthropic API (Prime direct)
                                            → Supabase Brain read/write
```

### Model routing logic (config.yaml)
```yaml
prime:
  provider: anthropic
  model: claude-opus-4-7
projectionist:
  provider: ollama
  model: qwen3:4b
archivist:
  provider: ollama
  model: qwen3:14b
contemplator:
  provider: ollama
  model: qwen3:14b
```

### Limitations
- Contemplator does not run between sessions — no inner life between interactions
- Mobile always hits Anthropic API — per-token cost, no local model benefit
- Workstation must be on and Ollama must be running for local inference
- No scheduling infrastructure

### Cost profile
- Anthropic API: per-token (Prime invocations + mobile fallback)
- Supabase: free tier sufficient
- Render: free tier sufficient

---

## T2 — Local Scheduled (Near-Term)

### What it is
Identical hardware to T1. The only new piece is a scheduler that gives Contemplator a persistent rhythm between sessions. This is what activates Helm's inner life — rumination, belief graduation, curiosity generation — without requiring user interaction.

### What changes from T1
- **APScheduler** added inside FastAPI (or external cron) triggers Contemplator on a configurable interval (e.g., every 2 hours, every morning at 06:00)
- Contemplator runs its no-think/think cycle against recent frames, writes outputs to Supabase via Archivist
- Prime opens next session with Contemplator's surfaced curiosities and belief updates
- Everything else identical to T1

### New infrastructure piece
```python
# Inside FastAPI startup (services/helm-runtime/scheduler.py)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_contemplator_cycle,
    trigger='cron',
    hour='*/2',           # Every 2 hours
    id='contemplator_cycle'
)
scheduler.start()
```

### Request flow
```
Scheduled (background, no user present):
Cron trigger → FastAPI → Contemplator (Ollama local) → Archivist → Supabase

On-demand (user-initiated):
Same as T1, plus Prime receives Contemplator output at session open
```

### What this unlocks
- Helm begins sessions with "I've been thinking about..." — genuine between-session inner life
- Belief graduation can operate on a cycle rather than only within sessions
- Morning check-in / evening SITREP becomes possible (scheduled Prime invocations)

### Cost profile
- Same as T1 — no new API cost
- Slightly higher local compute (Contemplator running 2–4x per day)

---

## T3 — Thor Always-On (Personal Ambient)

### What it is
The Thor replaces the 4090 workstation as the primary inference node. Thor runs 24/7. Agents live permanently in MIG partitions. Mobile now routes to Thor rather than falling back to the Anthropic API. Prime can run on Claude Max (flat subscription, no per-token cost) or a local 70B model. Contemplator becomes a true persistent background process.

### Infrastructure
- **Compute:** NVIDIA Thor (RTX 6000 Ada, 85GB VRAM, MIG partitioned)
- **MIG partition allocation:**

  | Partition | Subsystem | Model | VRAM allocation |
  |-----------|-----------|-------|-----------------|
  | MIG-0 | Helm Prime | Local 70B OR Claude Max SDK | 40GB |
  | MIG-1 | Archivist | Qwen3 14B | 20GB |
  | MIG-2 | Contemplator | Qwen3 14B | 20GB |
  | MIG-3 | Projectionist | Qwen3 4B | 5GB |

- **Inference:** vLLM or Ollama per partition — models preloaded, always warm
- **Prime options:**
  - **Claude Max subscription:** SDK call, flat monthly cost, no per-token charge
  - **Local 70B:** Llama 3.3 70B or equivalent, runs in MIG-0, zero marginal cost
- **Brain:** Supabase (unchanged)
- **Runtime:** FastAPI (unchanged), now always-on as a system service
- **Mobile gateway:** Render → Thor runtime (local config now available) — no Anthropic API fallback needed

### Request flow
```
Desktop:
User → FastAPI (Thor) → model_router.py → Ollama/vLLM (Thor MIG partitions)
                                        → Supabase Brain read/write

Mobile:
User → Render → Thor FastAPI (always reachable) → MIG partitions
                                                → Supabase Brain read/write

Background (Contemplator):
Persistent process → Contemplator MIG partition → Archivist → Supabase
```

### Model routing update (config.yaml)
```yaml
prime:
  provider: anthropic_sdk   # Claude Max — or switch to local:
  # provider: ollama
  # model: llama3.3:70b
  model: claude-opus-4-7
projectionist:
  provider: ollama
  model: qwen3:4b
  endpoint: http://thor-mig-3:11434
archivist:
  provider: ollama
  model: qwen3:14b
  endpoint: http://thor-mig-1:11434
contemplator:
  provider: ollama
  model: qwen3:14b
  endpoint: http://thor-mig-2:11434
```

### What this unlocks
- True T3 ambient — Helm has genuine always-on inner life
- Mobile is first-class — same experience as desktop, no API fallback
- Zero per-token cost (Claude Max subscription or fully local Prime)
- Contemplator runs continuously as a background process, not just on schedule
- Foundation for T3 surfaces: watch, home, ambient audio

### Cost profile
- Thor: one-time hardware (~$4,000–$5,000)
- Claude Max: flat subscription (if using SDK path for Prime)
- Supabase: free → Pro as memory volume grows
- Render: free tier sufficient for personal use
- Marginal inference cost: $0

---

## Productization — Multi-User Infrastructure

### What it is
A separate infrastructure layer built on top of the validated T3 architecture. Users do not own or run inference hardware. Hammerfall operates a shared GPU inference cluster. Each user gets their own isolated Brain in Supabase. The model is the same SaaS model as any cloud-hosted AI product.

**Critical distinction:** The model (weights, compute) is shared infrastructure. The Brain (memory, beliefs, personality, frames) is per-user and isolated. What makes each user's Helm feel like *their* Helm is the Brain, not the model.

### Infrastructure

```
Users (any surface)
       ↓
API Gateway (Render / Cloudflare)
Auth · rate limiting · session routing
       ↓
Helm Orchestration Service
Loads user Brain from Supabase
Routes to correct subsystem
Manages session lifecycle
       ↓
Shared GPU Inference Cluster
┌─────────────┬──────────────┬──────────────┬───────────────┐
│ Prime pool  │Projectionist │  Archivist   │ Contemplator  │
│ 70B shared  │  pool (4B)   │  pool (14B)  │  job queue    │
│ vLLM        │  high concur │  on-demand   │  async/sched  │
└─────────────┴──────────────┴──────────────┴───────────────┘
       ↓
Per-User Brain (Supabase — row-level security)
┌──────────┬──────────┬──────────┬──────────┐
│User A    │User B    │User C    │User N    │
│memories  │memories  │memories  │memories  │
│beliefs   │beliefs   │beliefs   │beliefs   │
│frames    │frames    │frames    │frames    │
│prefs     │prefs     │prefs     │prefs     │
└──────────┴──────────┴──────────┴──────────┘
```

### New infrastructure required (not in personal Helm)
- **API gateway:** Auth, rate limiting, user identification, session routing
- **Orchestration service:** Multi-tenant request handler — loads correct Brain per user, routes subsystem calls, manages concurrency
- **vLLM inference cluster:** Replaces per-user Ollama. One vLLM instance serves many concurrent users per model. GPU nodes on Lambda Labs / CoreWeave / RunPod
- **Background job queue:** Celery or equivalent — Contemplator runs as async jobs per user, scheduled independently per tier
- **Supabase row-level security:** Per-user Brain isolation enforced at database level
- **Billing integration:** Stripe — maps to tier, tracks usage where relevant

### GPU infrastructure options
| Provider | Best for | Notes |
|----------|----------|-------|
| Lambda Labs | Cost-effective A100/H100 | Good for stable workloads |
| CoreWeave | Flexible GPU types | Good Kubernetes support |
| RunPod | Bursty / variable load | Cheapest spot pricing |
| AWS / GCP | Enterprise compliance needs | 3–5x more expensive for raw GPU |

---

## Pricing Tiers

Pricing maps directly to which subsystems are active, which models serve them, and whether Contemplator runs continuously.

### Tier 0 — Free

**Positioning:** Try Helm. No commitment.

| Dimension | Value |
|-----------|-------|
| Prime | Smaller model (8B–14B) |
| Projectionist | Active |
| Archivist | Active — limited retrieval window (30 days) |
| Contemplator | Disabled |
| Memory window | 30 days |
| Surfaces | Web only |
| Proactivity tier | T1 — on-demand only |
| Inner life | None |

**Experience:** Helm responds well. Remembers recent sessions. No personality, no curiosity, no between-session thinking. Feels like a smart assistant, not a persistent presence.

---

### Tier 1 — Personal ($29/mo)

**Positioning:** One Helm, fully yours. Memory that compounds. Personality that calibrates.

| Dimension | Value |
|-----------|-------|
| Prime | Full Opus-class model |
| Projectionist | Active |
| Archivist | Active — 1 year retrieval window |
| Contemplator | Scheduled — 2x daily cycles |
| Memory window | 1 year |
| Surfaces | Web, mobile, desktop |
| Proactivity tier | T2 — scheduled check-ins |
| Inner life | Scheduled — morning/evening |
| Personality tuning | All 6 dimensions |
| Beliefs | Active — graduation enabled |

**Experience:** Helm feels genuinely persistent. He remembers what matters. He has opinions. He initiates morning check-ins and evening SITREPs. He's been thinking about things between sessions. This is the product as designed.

---

### Tier 2 — Ambient ($79/mo)

**Positioning:** Helm as presence, not tool. Always on. Always thinking.

| Dimension | Value |
|-----------|-------|
| Prime | Full Opus-class model — priority queue |
| Projectionist | Active |
| Archivist | Active — unlimited retrieval |
| Contemplator | Always-on — continuous background process |
| Memory window | Unlimited |
| Surfaces | Web, mobile, desktop, watch, voice (beta) |
| Proactivity tier | T3 — ambient, proactive surfacing |
| Inner life | Continuous — Helm initiates based on judgment |
| Personality tuning | All 6 dimensions + calibration suggestions |
| Beliefs | Active + Helm proposes belief updates for review |
| Feats (when available) | Full access |

**Experience:** This is JARVIS. Helm is always thinking. He surfaces things you didn't ask for because he's been processing. He knows when to speak and when to stay quiet. The relationship compounds at maximum rate.

---

### Tier 3 — Bring Your Own Hardware (BYOH) ($19/mo + hardware)

**Positioning:** For users who want Helm fully on-premise. Privacy-first. Zero cloud inference cost.

| Dimension | Value |
|-----------|-------|
| Prime | User's local model (70B recommended) |
| All subsystems | Running on user hardware |
| Memory window | Unlimited |
| Surfaces | All |
| Proactivity tier | T3 — ambient |
| Inner life | Continuous |
| Cloud dependency | Supabase Brain sync only |
| Anthropic API | Not required |

**Model:** Hammerfall provides the orchestration software, runtime, and Brain sync. User provides the GPU. Flat fee covers software license and Supabase hosting. No inference cost to Hammerfall beyond the Brain sync.

**Target user:** Privacy-conscious power users, enterprises, users with existing NVIDIA hardware (DGX Spark, workstation-class GPU, home lab).

---

## Infrastructure Cost Model (Productization)

Rough unit economics at scale for internal planning. Not for external communication.

| Cost driver | Estimate | Notes |
|-------------|----------|-------|
| Prime (70B) — per 1M tokens | ~$0.80–1.20 | vLLM on A100, shared across users |
| Projectionist (4B) — per 1M tokens | ~$0.05 | Cheap, high concurrency |
| Archivist (14B) — per 1M tokens | ~$0.20 | On-demand retrieval |
| Contemplator — per user/day | ~$0.04–0.08 | Async background job |
| Supabase — per user/month | ~$0.10–0.50 | Scales with memory volume |
| Render gateway — per user/month | ~$0.02 | Negligible at scale |

**Margin targets:**
- Free tier: -$0.15–0.30/user/month (acquisition cost)
- Personal ($29): ~65–70% gross margin at steady state
- Ambient ($79): ~55–60% gross margin (Contemplator always-on is the cost driver)
- BYOH ($19): ~85% gross margin (no inference cost)

---

## Productization Milestones

These are infrastructure milestones, not feature milestones. Feature roadmap lives in the Jarvana stages document.

| Milestone | Description | Depends on |
|-----------|-------------|------------|
| P0 | Thor bring-up, MIG partitioning, T3 personal Helm validated | Thor hardware |
| P1 | Orchestration service — multi-tenant request routing | P0 |
| P2 | Per-user Brain isolation — Supabase RLS, user provisioning | P1 |
| P3 | Shared inference cluster — vLLM, first external GPU node | P2 |
| P4 | Contemplator job queue — per-user scheduled background jobs | P3 |
| P5 | Billing integration — Stripe, tier enforcement | P4 |
| P6 | First external user onboarding | P5 |

**Current state:** T1 personal instance. P0 is next hardware milestone.

---

## Key Architectural Decisions and Rationale

**Supabase as SSoT from day one.**
The Brain is in Supabase from T1. This means productization doesn't require a data migration — every user's Brain is already in the right place. The only productization work is adding isolation (RLS) and multi-tenant routing.

**Model router abstraction from day one.**
`model_router.py` wrapping LiteLLM means switching from local Ollama to cloud vLLM to Anthropic API is a config change, not a code change. Tier changes, hardware upgrades, and model swaps don't touch agent logic.

**Agents are stateless functions, not persistent processes.**
State lives in Supabase. Agents load state on invocation and write state back on completion. This is what makes horizontal scaling tractable — you can add inference workers without coordination overhead, because none of them hold state.

**Contemplator is the primary cost driver.**
Every other subsystem is on-demand. Contemplator is the one that runs continuously for ambient-tier users. Infrastructure sizing, pricing, and GPU allocation all center on Contemplator's always-on requirement. This is the unit to optimize.

**BYOH tier preserves personal-instance architecture.**
The T3 personal Helm (Thor + local models) is the exact same architecture as the BYOH product tier. The software is the same. The only difference is who operates the hardware. This means Maxwell's personal instance doubles as a living demo and validation environment for the BYOH product.

---

*This document is maintained alongside the Jarvana roadmap. Update when infrastructure decisions change. Do not update for feature changes — those belong in the stage documents.*
