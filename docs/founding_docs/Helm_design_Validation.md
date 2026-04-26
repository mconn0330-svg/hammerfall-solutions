# Helm Design Validation Brief
**Purpose:** Codebase verification against architectural theory  
**Audience:** Helm IDE (Claude Opus) — read alongside the live codebase  
**Companion documents:** `Helm_The_Ambient_Turn.md` (vision), `HELM_PRODUCTIZATION.md` (tier model)  
**Output requested:** Structured verdict per section — Aligned / Deviated / Gap — with specific file and line references where relevant  

---

## Context

This document captures the architectural theory established during a planning session. The theory may have evolved ahead of the implementation. Your job is to identify where the codebase matches the theory, where it deviates, and where gaps exist that will need to be filled before the architecture is coherent.

Do not assume the theory is correct and the code is wrong — or vice versa. Flag both directions. If the code has solved something better than the theory describes, say so.

---

## The Theory in Plain Terms

Before diving into verification points, here is the architectural model as understood. Use this as your reference frame.

**The repo is the app.** All logic — FastAPI, agent definitions, memory module, provider chain, subsystem prompts — lives in the repository. Without a running process it is inert code.

**FastAPI is the process.** `docker compose up` starts FastAPI. FastAPI is what turns the repo into a live runtime. Its job is narrow: receive HTTP requests, route them to the right function, return responses. It knows nothing about AI specifically — it is a web framework.

**The runtime is code plus running process.** Local runtime = FastAPI running in Docker on the developer's machine. Cloud runtime = the same code running on Render, publicly accessible at all times. Same codebase, different deployment target.

**model_router.py implements the provider chain.** The provider chain is the ordered list of model providers per agent slot (e.g. `claude-sdk → local → anthropic-api`). model_router.py reads config.yaml and walks that list, using the first available provider. This is the mechanism that makes Helm model-agnostic and hardware-flexible.

**The four subsystems are distinct invocation paths.** Helm Prime, Projectionist, Archivist, and Contemplator are not a monolith. Each is a separate agent role with its own provider chain configuration, its own model, and its own invocation path through FastAPI.

**All Brain writes go through the memory module.** No agent calls Supabase directly for writes. The memory module is the single write path. brain.sh discipline enforces this. Reads may still go through a direct client (read_client.py) but writes are unified.

**Supabase is the single source of truth.** Every surface, every runtime instance, every subsystem reads from and writes to the same Supabase project. This is what gives Helm persistent identity across sessions and surfaces.

**The provider chain is user-configurable via config.yaml.** Changing which model serves an agent slot requires only a config change — no code change. This is load-bearing for the productization tier model where different users have different infrastructure.

---

## Verification Sections

Work through each section against the codebase. Return a verdict for each and note specific files, functions, or line numbers where relevant.

---

### Section 1 — FastAPI Runtime Shape

**Theory:**
- FastAPI is the entry point for all runtime requests
- Core endpoints: `POST /invoke/{agent_role}`, `GET /events` (SSE), `GET /health`
- `/health` requires no auth (used by Docker healthcheck and monitoring)
- `/invoke/*` and `/events` require bearer token auth (HELM_API_TOKEN)
- Correlation IDs are generated per request and propagated through structured logs

**Verify:**
1. Does `main.py` (or equivalent entry point) instantiate a FastAPI app?
2. Do the three core endpoints exist with the described signatures?
3. Is bearer token middleware applied to `/invoke` and `/events` but not `/health`?
4. Is correlation ID generation implemented per request?
5. Is there a structured logging convention (structlog or equivalent) in place?

**Flag if:** Endpoints are missing, auth is absent or applied incorrectly, logging is still print statements, or the entry point is not FastAPI.

---

### Section 2 — Provider Chain Implementation

**Theory:**
- `model_router.py` reads `config.yaml` to determine which provider serves each agent slot
- Provider chain is an ordered list: the router tries each in sequence, falls back on failure
- Three provider types: `claude-sdk` (Claude Max subscription), `local` (Ollama endpoint), `anthropic-api` (pay-per-token API key)
- Provider selection is entirely config-driven — no provider is hardcoded in agent logic
- Each provider runs a startup probe to determine availability; unavailable providers are skipped

**Verify:**
1. Does `config.yaml` exist and contain per-agent provider chain definitions?
2. Does `model_router.py` read from config rather than hardcoding provider logic?
3. Is fallback logic implemented — does it actually try the next provider on failure?
4. Are the three provider types (`claude-sdk`, `local`, `anthropic-api`) implemented as distinct backends?
5. Is there a startup probe or availability check per provider?
6. Is any provider hardcoded in agent code rather than driven by config?

**Flag if:** Provider is hardcoded anywhere outside config, fallback logic is absent, only one provider type is implemented, or config.yaml does not exist.

---

### Section 3 — Subsystem Architecture

**Theory:**
- Four distinct subsystems: Helm Prime, Projectionist, Archivist, Contemplator
- Each is a separate agent role reachable via `/invoke/{agent_role}`
- Each has its own provider chain in config (different models, different endpoints)
- Subsystems are cognitive subdivisions of one mind — not independent agents with their own identity
- Contemplator runs on a schedule (cron/APScheduler) between sessions at T2, not only within sessions
- Speaker was removed — there is no fifth subsystem

**Verify:**
1. Are all four subsystems defined as distinct invocable roles?
2. Does each have its own entry in config.yaml with its own provider chain?
3. Is there any remaining reference to Speaker in the codebase (agent definitions, prompts, routing logic, mock data)?
4. Is Contemplator invocable both on-demand (within session) and on a schedule?
5. Is there a scheduler (APScheduler or equivalent) wired to trigger Contemplator cycles?
6. Are subsystems truly separate invocation paths or does one endpoint handle all with a switch statement?

**Flag if:** Speaker references remain anywhere, subsystems share a monolithic invocation path, Contemplator has no scheduled trigger, or config treats subsystems identically rather than with distinct model assignments.

---

### Section 4 — Memory Module and Brain Write Discipline

**Theory:**
- A unified memory module handles all Brain writes — no agent writes to Supabase directly
- Write path: agent code → `memory.write()` → outbox (SQLite) → drain to Supabase
- Outbox uses SQLite (not JSONL) for concurrency safety and crash durability
- Circuit breaker wraps Supabase calls — opens on repeated failures, emits observability events
- Contemplator writes go through Archivist, never directly
- All shell scripts that previously called brain.sh have been replaced with memory module calls
- `supabase_client.py` has been renamed `read_client.py` to make the write/read split explicit
- The following files were rewritten to remove brain.sh references: `helm_prompt.md`, `archivist.md`, `contemplator.md`, `COMPANY_BEHAVIOR.md`

**Verify:**
1. Does a memory module exist (`memory/` package or equivalent)?
2. Does `memory.write()` (or equivalent) exist as the unified write interface?
3. Is an outbox implemented? Is it SQLite-backed (not JSONL)?
4. Is a circuit breaker implemented around Supabase calls?
5. Is `supabase_client.py` renamed to `read_client.py` or equivalent?
6. Search for direct Supabase insert/post calls in agent code — do any exist outside the memory module?
7. Search for `brain.sh` references in prompt files and agent definitions — do any remain?
8. Are the four listed prompt/doc files free of brain.sh references?
9. Does Contemplator route its writes through Archivist rather than writing directly?

**Flag if:** Direct Supabase writes exist in agent code, the outbox is still JSONL, brain.sh references remain in prompt files, or Contemplator writes bypass Archivist.

---

### Section 5 — Supabase Brain Schema

**Theory:**
The Brain contains the following tables at minimum:
- `helm_memory` — general memory writes, all types
- `helm_beliefs` — Helm's accumulated beliefs (with graduation mechanism)
- `helm_frames` — structured session memory records (written by Projectionist)
- `helm_entities` — people, projects, concepts Helm tracks (with type, aliases, attributes)
- `helm_entity_relationships` — relationships between entities
- `helm_personality` — the six tunable personality dimensions per user
- `helm_curiosities` — open curiosity flags (T0.B7b)
- `helm_promises` — commitments Helm makes (T0.B7c)
- `helm_signals` — dual-write mirror of pattern-type memory entries

All tables have RLS policies. All tables have Supabase Realtime enabled.

pgvector extension is installed for semantic memory search.

**Verify:**
1. Do all listed tables exist in the schema?
2. Do `helm_curiosities` and `helm_promises` exist (T0.B7 Tier 2 types)?
3. Is `helm_entities` enriched with `entity_type`, `aliases`, `attributes`, `first_mentioned_at`, `last_mentioned_at`, `salience_decay`?
4. Does `helm_entity_relationships` exist?
5. Are RLS policies applied to all tables?
6. Is Realtime enabled on all tables?
7. Is pgvector installed and used for semantic search on memory retrieval?
8. Is there a schema baseline committed (`supabase/schema_baseline.sql`)?

**Flag if:** Any table is missing, Tier 2 types are absent, pgvector is not installed, RLS is missing on any table, or no schema baseline exists.

---

### Section 6 — Surface and Routing Architecture

**Theory:**
- Vercel hosts the UI (static files — React/HTML/CSS/JS)
- Render hosts the FastAPI runtime (the running process, publicly accessible)
- Mobile and remote surfaces hit Render; Render routes to wherever models live
- Desktop hits the local FastAPI runtime directly when on the same machine
- Smart routing is implemented in the UI: probe local first, fall back to Render/remote if unreachable
- Smart routing state machine has six states: startup probe, active local, active remote, failover to remote, re-probe local, no runtime reachable
- Tailscale connects Render's runtime container to the local machine/Thor for model access without public IP exposure
- There is NO model inference happening on Render itself — Render only runs FastAPI

**Verify:**
1. Is there a Vercel config or deployment target for the UI?
2. Is there a Render config (`render.yaml`) for the runtime service?
3. Is smart routing implemented in the UI client? Does it probe a local URL first?
4. Is there a banner component for routing state (amber = on remote, red = unreachable)?
5. Is Tailscale integration present in the Dockerfile or startup scripts?
6. Is there any model inference code running on Render directly (this should not exist)?
7. Does the UI have environment variables for both `VITE_HELM_LOCAL_URL` and `VITE_HELM_REMOTE_URL`?

**Flag if:** Smart routing is absent, Tailscale is not integrated, models are being called directly from Render without routing through a provider endpoint, or the UI has no awareness of local vs remote runtime.

---

### Section 7 — Observability and Operational Readiness

**Theory:**
- structlog is the logging standard — all logs are structured JSON, not print statements
- Every log event includes a `correlation_id` bound per request
- Logger naming convention: `helm.<module>` (e.g. `helm.memory`, `helm.agent.contemplator`)
- OpenTelemetry tracer is initialized (no exporter yet — spans are structured but not shipped)
- Three guardrail layers: rate alarm (all providers), Pro Max weekly tracker (claude-sdk only), dollar cap (anthropic-api only)
- `/health` endpoint returns structured status including outbox queue depth and circuit breaker state
- A `runbooks/` directory exists with at minimum the API token rotation and Supabase backup runbooks

**Verify:**
1. Is structlog imported and configured at application startup?
2. Are print statements absent from runtime-critical code paths?
3. Is correlation ID middleware present on FastAPI?
4. Are logger names following `helm.<module>` convention?
5. Is OpenTelemetry initialized (even without exporter)?
6. Are the three guardrail layers implemented in a `guardrails.py` or equivalent?
7. Does `/health` return structured JSON including outbox and circuit breaker state?
8. Does `docs/runbooks/` exist with at minimum two runbook files?

**Flag if:** print statements are the primary logging mechanism, correlation IDs are absent, guardrails are not implemented, `/health` returns only a simple OK, or no runbooks exist.

---

### Section 8 — CI and Repo Discipline

**Theory:**
- `AGENTS.md` exists at repo root as the vendor-neutral operating contract
- Conventional Commits are enforced via commitlint
- GitHub Actions CI runs on every PR: lint (ruff/eslint), type check (mypy), test (pytest/vitest), build
- A test harness exists: pytest for Python, vitest for JavaScript
- Migration discipline: numbered SQL migrations in `supabase/migrations/`, schema baseline committed
- Secrets scanning (gitleaks) runs on every push
- Dependabot is configured for automated dependency updates
- No CLAUDE.md at repo root — vendor-neutral AGENTS.md is the standard

**Verify:**
1. Does `AGENTS.md` exist at repo root?
2. Does `commitlint.config.js` exist with the allowed types and scopes?
3. Does `.github/workflows/ci.yml` exist and run lint + type check + test?
4. Does a pytest configuration exist (`pyproject.toml` with `[tool.pytest.ini_options]`)?
5. Does a vitest configuration exist (`vitest.config.js`)?
6. Does `supabase/migrations/` contain numbered migration files?
7. Does `supabase/schema_baseline.sql` exist?
8. Does `.github/workflows/gitleaks.yml` or equivalent secrets scanning exist?
9. Does `.github/dependabot.yml` exist?
10. Is `CLAUDE.md` absent from repo root (replaced by `AGENTS.md`)?

**Flag if:** AGENTS.md is absent, CI does not exist or does not run tests, no test harness is configured, migrations are ad-hoc SQL without numbering, or CLAUDE.md is still the operating contract.

---

### Section 9 — Docker and Deployment

**Theory:**
- `docker-compose.yml` orchestrates: FastAPI runtime + Ollama sidecar (minimum)
- Dockerfile is multi-stage: builder stage installs dependencies, runtime stage is minimal
- Runtime container runs as non-root user
- HEALTHCHECK is defined in Dockerfile
- `.dockerignore` exists to keep image size small
- Base image is pinned to a specific version (not `latest`)
- `render.yaml` defines the Render service configuration
- Tailscale startup script (`start-with-tailscale.sh`) exists in the runtime service

**Verify:**
1. Does `docker-compose.yml` define both the runtime and Ollama services?
2. Is the Dockerfile multi-stage?
3. Does the Dockerfile create and switch to a non-root user?
4. Is `HEALTHCHECK` defined in the Dockerfile?
5. Does `.dockerignore` exist?
6. Is the base image pinned to a specific version tag?
7. Does `render.yaml` exist at repo root?
8. Does `scripts/start-with-tailscale.sh` or equivalent exist?

**Flag if:** Dockerfile builds as root, no HEALTHCHECK, base image uses `latest`, docker-compose does not include Ollama, or no Render deployment config exists.

---

### Section 10 — Identity and Prompt Integrity

**Theory:**
- Helm has three identity layers: Prime Directives (immutable), Identity Baseline (stable), Personality Tuning (user-adjustable 0.0–1.0 on six dimensions)
- The six personality dimensions: Directness, Challenge frequency, Verbosity, Formality, Show reasoning, Sarcasm
- Prime Directives are: Do not harm, Do not deceive, State uncertainty, Human in the loop
- Helm's prompts reflect this layered structure
- Speaker has been fully removed — no references remain in any prompt file
- Personality scores are stored in `helm_personality` table and loaded into Prime's context at session start
- The prompt management system (PromptManager) handles loading prompts from Supabase with file fallback

**Verify:**
1. Does `helm_prompt.md` reflect the three-layer identity structure?
2. Are the four Prime Directives present and immutable in the prompt?
3. Are the six personality dimensions defined and referenced in the prompt?
4. Is Speaker absent from all prompt files?
5. Is personality loaded from `helm_personality` at session start and injected into Prime's context?
6. Does a PromptManager exist that loads from Supabase with file fallback?
7. Does the prompt reflect memory module API calls rather than brain.sh commands?

**Flag if:** Prime Directives are absent or soft, personality dimensions are not defined, Speaker appears anywhere in prompts, personality scores are hardcoded rather than loaded from Brain, or brain.sh syntax remains in prompt files.

---

## Output Format Requested

Return your findings in this structure for each section:

```
### Section N — [Name]

Verdict: [Aligned / Partially Aligned / Deviated / Gap]

Findings:
- [specific finding with file/line reference]
- [specific finding with file/line reference]

Deviations from theory:
- [what the theory says vs what the code does]

Gaps (theory describes something not yet implemented):
- [what is missing]

Recommendations:
- [specific action needed to align code with theory]
```

---

## Meta-Instructions

- Be specific. File names and line numbers are more useful than general observations.
- Do not soft-pedal deviations. If something is wrong, say it directly.
- If you find the code has solved something better than the theory describes, flag it as a positive deviation and explain why.
- If a section is fully aligned with no gaps, say so clearly and move on.
- If you encounter something in the codebase that the theory does not account for at all, flag it in a final **Unaccounted Elements** section at the end.
- The goal is a complete, honest picture of where the theory and implementation meet — and where they don't.

---

## Priority Order

If time or context is limited, prioritize sections in this order:

1. Section 2 — Provider Chain (most architecturally load-bearing)
2. Section 4 — Memory Module and Brain Write Discipline (most likely to have gaps)
3. Section 3 — Subsystem Architecture (Speaker removal, Contemplator scheduling)
4. Section 1 — FastAPI Runtime Shape (foundational)
5. Section 5 — Supabase Brain Schema (data integrity)
6. Sections 6–10 (operational, deployment, CI)

---

*This document was produced as a companion to the Helm architecture planning session. It reflects the theory as understood at the time of authoring. Treat it as a hypothesis to be verified, not a ground truth.*
