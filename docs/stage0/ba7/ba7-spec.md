# BA7 — Helm Runtime Service: Technical Specification
## Proving Ground → Production Foundation

> **Historical document — frozen at the date below.** References to "Speaker" reflect the pre-Ambient Turn architecture. Speaker was deprecated in Lane C Phase 3 (PRs #78 code deletion, #79 contract archival, #80 reference scrub). Current architecture: `docs/founding_docs/Helm_The_Ambient_Turn.md`. Deprecation rationale: `docs/archive/speaker-deprecated/`.

**Version:** Pre-build spec
**Date:** 2026-04-12
**Status:** Approved for implementation
**Closes:** Stage 0

---

## 1. What BA7 Is

BA7 builds the **Helm Runtime Service** — a provider-agnostic orchestration layer that
routes agent role requests to the correct model backend. It is the separation of
*who does the work* (agent contracts) from *what model executes it* (provider config).

At Stage 0, the runtime runs locally. At Stage 4 (Hammerfall Cloud), the same service
deploys unchanged to cloud infrastructure. Same code. Different config target.

**BA7 achieves four things:**

1. **Multi-agent orchestration foundation.** Projectionist and Archivist execute as
   routed service calls — not inline Claude Code subprocesses. Each agent role has a
   dedicated execution path. Helm Prime's context window is freed from memory logistics.
   The conveyor belt runs independently.

2. **Multi-model routing.** Helm Prime runs on Claude. Projectionist and Archivist run
   on a small local model (Qwen2.5 3B via Ollama). Speaker is configurable. Every role
   has its own model assignment. The routing layer enforces this without Helm Prime
   knowing or caring which model is downstream.

3. **BYO model foundation.** Any agent role's model is a single config line change.
   Anthropic, OpenAI, Ollama, or any OpenAI-compatible endpoint. No code changes.
   This is the BYO model promise delivered at the infrastructure layer.

4. **Stage 4 compatibility.** The service is containerized from day one. Docker-based.
   Provider-agnostic. All service URLs come from config. Deploy to any cloud target
   by changing one config file.

---

## 2. What BA7 Is Not

- Not Quartermaster. No user management, no billing, no product surface.
- Not the full middleware pipeline. Prime Directives guard and personality injection
  hooks are scaffolded (stubs only) — not implemented.
- Not a real-time voice layer. Speaker remains on Claude Code at T1.
- Not brain provisioning. Supabase setup is already complete from BA6.
- Not an orchestration framework (no LangGraph, no Celery). Thin Python service only.

---

## 3. Architecture Overview

```
Claude Code (T1 — session host)
│
│  Routine 0 — session start
│  Routine 4 — post-response writes
│
│  [Bash tool: curl POST /invoke/projectionist]
│  [Bash tool: curl POST /invoke/archivist]
│
▼
┌─────────────────────────────────────────────────┐
│             Helm Runtime Service                 │
│             (FastAPI — port 8000)                │
│                                                  │
│  POST /invoke/{agent_role}                       │
│  GET  /health                                    │
│  GET  /config/agents                             │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Middleware Pipeline               │   │
│  │  [Pre]  session_context_inject (active)  │   │
│  │  [Pre]  personality_inject (stub)        │   │
│  │  [Pre]  prime_directives_guard (stub)    │   │
│  │  [Post] output_validator (active)        │   │
│  │  [Post] prime_directives_output (stub)   │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │           Model Router                    │   │
│  │  Reads config.yaml                        │   │
│  │  Resolves provider + model per role       │   │
│  │  Routes via LiteLLM                       │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         supabase_client.py               │   │
│  │  httpx POST to Supabase REST API         │   │
│  │  Replaces brain.sh subprocess path       │   │
│  │  Used by Archivist agent handler         │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
  ┌─────────────┐          ┌──────────────┐
  │   Ollama    │          │   Supabase   │
  │  (local)    │          │   Brain      │
  │ port 11434  │          │ helm_frames  │
  │ qwen2.5:3b  │          │ helm_memory  │
  └─────────────┘          └──────────────┘
```

**Invocation model — Option B (confirmed):**
Helm Prime's `helm_prompt.md` Routine 0 and Routine 4 are updated to invoke the
runtime via `Bash` tool curl calls. The Agent tool is removed from the
Projectionist/Archivist invocation path. The runtime IS the coordination
mechanism — not a subprocess behind it.

At T3, the Agent tool disappears entirely. Helm Prime → runtime is the permanent
production model. BA7 builds that model now at T1.

---

## 4. Service File Structure

```
services/
└── helm-runtime/
    ├── main.py                    # FastAPI app, endpoint definitions, startup
    ├── model_router.py            # Config loading, provider resolution, LiteLLM dispatch
    ├── middleware.py              # Middleware pipeline — active hooks + stubs
    ├── supabase_client.py         # Supabase REST write/read — replaces brain.sh in Python
    ├── agents/
    │   ├── projectionist.py       # Projectionist role handler
    │   └── archivist.py           # Archivist role handler
    ├── config.yaml                # Agent-to-model mapping — the BYO contract
    ├── requirements.txt           # Version-pinned Python dependencies
    └── Dockerfile                 # Python 3.11 slim, all deps pinned

docker-compose.yml                 # Runtime service + Ollama sidecar
scripts/
└── smoke_test.sh                  # End-to-end validation — all 6 checks
```

---

## 5. Configuration Schema — config.yaml

This file is the BYO model contract. Swapping any model is one line + service restart.
No code changes. All service URLs are read from this file — no hardcoded defaults in code.

```yaml
# config.yaml — Helm Runtime Service configuration
# Provider types: anthropic, openai, ollama, custom
# Custom = any OpenAI-compatible endpoint (most open-source model servers)

service:
  port: 8000
  log_level: info

supabase:
  url_env: SUPABASE_BRAIN_URL              # env var name — value never in config
  service_key_env: SUPABASE_BRAIN_SERVICE_KEY

agents:
  helm_prime:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
    # No base_url — Anthropic uses default endpoint

  projectionist:
    provider: ollama
    model: qwen2.5:3b
    base_url_env: OLLAMA_BASE_URL          # env var — default: http://localhost:11434
    # api_key_env: not required for ollama

  archivist:
    provider: ollama
    model: qwen2.5:3b
    base_url_env: OLLAMA_BASE_URL
    # Shares Ollama instance with Projectionist — different role, same model, same server

  speaker:
    provider: ollama
    model: llama3.1:8b
    base_url_env: OLLAMA_BASE_URL
```

**Provider type reference:**

| Provider | Use Case | Required Config |
|---|---|---|
| `anthropic` | Helm Cloud default, BYO Claude key | `api_key_env` |
| `openai` | BYO OpenAI key | `api_key_env` |
| `ollama` | Local dev, Helm Self-Hosted | `base_url_env` |
| `custom` | Any OpenAI-compatible endpoint | `base_url_env`, `api_key_env` (optional) |

**BYO model examples — what config changes look like in practice:**

```yaml
# User with Anthropic key wants Haiku for Projectionist (cheaper):
projectionist:
  provider: anthropic
  model: claude-haiku-4-5-20251001
  api_key_env: ANTHROPIC_API_KEY

# Power user running their own LM Studio instance:
projectionist:
  provider: custom
  model: qwen2.5-3b-instruct
  base_url_env: LM_STUDIO_URL    # set to http://localhost:1234/v1

# Helm Cloud production config (Hammerfall-hosted model endpoint):
projectionist:
  provider: custom
  model: hammerfall-projectionist-v1
  base_url_env: HAMMERFALL_MODEL_URL
  api_key_env: HAMMERFALL_API_KEY
```

**Design rule — enforced in code:** `model_router.py` resolves all URLs and keys from
environment variables. Environment variable *names* live in `config.yaml`. The values
never appear in config. This rule holds at every tier.

---

## 6. API Contract

### POST /invoke/{agent_role}

Routes a request to the model configured for `agent_role`. Streams the response.

**Path parameter:** `agent_role` — one of `projectionist`, `archivist`, `speaker`, `helm_prime`

**Request body:**
```json
{
  "session_id": "uuid-v4 — generated by Claude Code at session start via crypto.randomUUID()",
  "turn_number": 14,
  "user_message": "verbatim user message — full text, no truncation",
  "helm_response": "verbatim Helm Prime response — full text, no truncation",
  "context": {
    "project": "hammerfall-solutions",
    "agent": "helm"
  }
}
```

**Notes on the request contract:**
- `session_id` is generated by Claude Code in Routine 0. The runtime is stateless —
  it does not generate or track session IDs. All session context is caller-supplied.
- `turn_number` is tracked by Claude Code as `TURN_COUNT`, incremented each message.
- `user_message` and `helm_response` are both required for frame creation.
  Projectionist needs the full turn to build a complete frame.
- The runtime passes `session_id` and `turn_number` into the agent handler.
  The agent handler is responsible for constructing the correct Supabase payload.

**Response:** Streamed agent output. For Projectionist: the frame JSON it constructed
and wrote. For Archivist: confirmation of migration or failure detail.

**Error responses:**
```json
{ "error": "unknown_role", "detail": "No configuration found for role: [role]" }
{ "error": "model_unreachable", "detail": "Provider [provider] at [url] is not responding" }
{ "error": "validation_failed", "detail": "Agent output failed schema validation", "raw": "[raw output]" }
```

---

### GET /health

Returns service health. Checks three things: runtime service up, all configured
model endpoints reachable, Supabase REST API and `helm_frames` table queryable.

**Response — healthy:**
```json
{
  "status": "healthy",
  "checks": {
    "service": "ok",
    "models": {
      "projectionist": { "status": "ok", "provider": "ollama", "model": "qwen2.5:3b" },
      "archivist": { "status": "ok", "provider": "ollama", "model": "qwen2.5:3b" },
      "helm_prime": { "status": "ok", "provider": "anthropic", "model": "claude-sonnet-4-6" }
    },
    "supabase": { "status": "ok", "table": "helm_frames", "rows_queryable": true }
  }
}
```

**Response — partial failure (returns 200, not 500 — health check surfaces the failure):**
```json
{
  "status": "degraded",
  "checks": {
    "service": "ok",
    "models": {
      "projectionist": { "status": "unreachable", "provider": "ollama", "error": "connection refused at http://localhost:11434" },
      ...
    },
    "supabase": { "status": "ok", ... }
  }
}
```

**Design note:** Health returns HTTP 200 in all cases — degraded or healthy. The `status`
field tells the caller the real state. HTTP 500 is reserved for the health endpoint
itself failing (runtime process error), not for downstream dependency failures.

---

### GET /config/agents

Returns the current agent-to-model mapping. No secrets exposed — only provider type,
model name, and resolved base URL (not API keys).

```json
{
  "agents": {
    "projectionist": { "provider": "ollama", "model": "qwen2.5:3b", "base_url": "http://localhost:11434" },
    "archivist": { "provider": "ollama", "model": "qwen2.5:3b", "base_url": "http://localhost:11434" },
    "helm_prime": { "provider": "anthropic", "model": "claude-sonnet-4-6" },
    "speaker": { "provider": "ollama", "model": "llama3.1:8b", "base_url": "http://localhost:11434" }
  }
}
```

---

## 7. Middleware Pipeline

The pipeline runs on every `/invoke/{role}` request. Pre-model hooks run before the
model call. Post-model hooks run after model output is received, before returning to caller.

BA7 scaffolds the full pipeline. Active hooks are implemented. Stub hooks are empty
pass-throughs with a `# TODO: [BA-phase]` comment indicating when they get implemented.

```python
# middleware.py — pipeline structure

class MiddlewarePipeline:
    def run_pre(self, role: str, request: InvokeRequest) -> InvokeRequest:
        request = self.session_context_inject(role, request)  # ACTIVE
        request = self.personality_inject(role, request)       # STUB — BA8
        request = self.prime_directives_guard(role, request)   # STUB — BA9
        return request

    def run_post(self, role: str, output: str) -> str:
        output = self.output_validator(role, output)           # ACTIVE
        output = self.prime_directives_output(role, output)    # STUB — BA9
        return output
```

**Active hooks at BA7:**

**`session_context_inject` (pre):**
Injects `session_id`, `turn_number`, and `project` into the prompt context passed to
the model. Ensures these fields are always present without the agent handler having
to remember to add them.

**`output_validator` (post):**
For Projectionist calls: validates the model output is valid JSON matching the frame
schema (required fields present, `frame_status` is a valid enum value). On failure:
logs the raw output, returns a structured error to the caller. The frame write never
happens on validation failure — no garbage gets written to the brain.

**Stub hooks — scaffolded, not implemented:**

**`personality_inject` (pre — BA8):**
Will load `helm_personality` scores from Supabase and inject them into the system
prompt for applicable roles. Stub returns request unchanged.

**`prime_directives_guard` (pre — BA9):**
Will validate the incoming request does not ask the model to violate a Prime Directive
before the call is made. Stub returns request unchanged.

**`prime_directives_output` (post — BA9):**
Will scan model output for Prime Directive violations before returning to caller.
Stub returns output unchanged.

---

## 8. supabase_client.py

Replaces `brain.sh` subprocess calls inside the Python service. Direct `httpx` async
POST to Supabase REST API. Both Projectionist and Archivist use this. One consistent
write path. No OS dependency. No path dependency. Docker-clean.

```python
# supabase_client.py — thin Supabase REST client

import httpx
import os
from typing import Any

class SupabaseClient:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def insert(self, table: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/{table}",
                json=payload,
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def patch(self, table: str, filters: dict, payload: dict) -> dict:
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/{table}?{query}",
                json=payload,
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def delete(self, table: str, filters: dict) -> None:
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.url}/rest/v1/{table}?{query}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()

    async def select(self, table: str, params: dict) -> list:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/{table}?{query}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> bool:
        try:
            await self.select("helm_frames", {"select": "id", "limit": "1"})
            return True
        except Exception:
            return False
```

**Relationship to brain.sh:**
`brain.sh` remains the canonical write tool for Claude Code shell contexts (Helm Prime,
Routine 4, snapshot.sh, sync_projects.sh). It is NOT replaced globally. `supabase_client.py`
is the Python equivalent used exclusively within the Helm Runtime Service. Two contexts,
two tools, one Supabase endpoint.

---

## 9. model_router.py

Loads `config.yaml` at service startup. Resolves provider and model for each agent role.
Dispatches to LiteLLM with the correct provider parameters. LiteLLM handles all provider
normalization — the router never calls Anthropic, OpenAI, or Ollama directly.

```python
# model_router.py — key behavior

class ModelRouter:
    def __init__(self, config_path: str):
        self.config = yaml.safe_load(open(config_path))
        self.agent_configs = self._resolve_configs()

    def _resolve_configs(self) -> dict:
        # For each agent, resolve env var values
        # api_key_env → os.environ[api_key_env]
        # base_url_env → os.environ[base_url_env]
        # Missing required env var → raise at startup, not at request time
        ...

    async def invoke(self, role: str, messages: list, stream: bool = True):
        agent_cfg = self.agent_configs.get(role)
        if not agent_cfg:
            raise UnknownRoleError(role)

        # LiteLLM model string format: "provider/model"
        # e.g. "anthropic/claude-sonnet-4-6", "ollama/qwen2.5:3b"
        model_string = f"{agent_cfg['provider']}/{agent_cfg['model']}"

        kwargs = {"model": model_string, "messages": messages, "stream": stream}
        if agent_cfg.get("api_key"):
            kwargs["api_key"] = agent_cfg["api_key"]
        if agent_cfg.get("base_url"):
            kwargs["base_url"] = agent_cfg["base_url"]

        return await litellm.acompletion(**kwargs)
```

**Startup validation:** On service start, `_resolve_configs()` resolves all env vars.
If a required env var is missing, the service fails to start with a clear error naming
the missing variable. Missing env vars are discovered at startup — not silently at
request time.

---

## 10. Projectionist Agent Handler (agents/projectionist.py)

Receives a turn request, builds the frame JSON, validates it, writes to `helm_frames`
via `supabase_client.py`.

**Prompt design:**
```
System: You are the Projectionist. Your only job is to analyze a conversation turn
and produce a structured JSON frame. Return ONLY valid JSON. No explanation, no preamble.
The JSON must exactly match the schema below.

Schema:
{
  "turn": <integer>,
  "timestamp": "<ISO 8601>",
  "user_id": "maxwell",
  "session_id": "<uuid>",
  "user": "<verbatim user message>",
  "helm": "<verbatim helm response>",
  "topic": "<inferred — project codename or topic area>",
  "domain": "<inferred — architecture|process|people|ethics|decisions|other>",
  "entities_mentioned": ["<name>", ...],   // empty array if none, never null
  "belief_links": ["<belief-slug>", ...],  // empty array if none, never null
  "frame_status": "active",
  "superseded_reason": null,
  "superseded_at_turn": null
}

Rules:
- entities_mentioned: proper nouns only — people, projects, companies
- belief_links: slugs from helm_beliefs domain — infer from context
- topic: short phrase, no more than 5 words
- domain: one value from the enum only
- Return ONLY the JSON object. Nothing else.
```

**Ollama JSON mode:** Every Projectionist call includes `"format": "json"` in the Ollama
API request. Forces valid JSON at the model level. Combined with post-model validation.

**Validation:** `output_validator` middleware checks:
1. Output is parseable JSON
2. Required fields present: `turn`, `session_id`, `user`, `helm`, `topic`, `domain`, `frame_status`
3. `frame_status` is one of `active`, `superseded`, `canonical`
4. `entities_mentioned` and `belief_links` are arrays (not null)

On validation failure: log raw output at ERROR level with session_id and turn_number.
Return structured error. Frame write does not happen.

**Latency expectation:** 200–500ms on 4090 with Qwen2.5 3B at the structured prompt
length used above. This is post-response — Maxwell is already reading Helm's reply.
Not on the critical path.

---

## 11. Archivist Agent Handler (agents/archivist.py)

Receives a frame migration request. Reads cold frames from `helm_frames`. For each
frame, generates a 1–3 sentence summary via the model, writes to `helm_memory` via
`supabase_client.py`, then deletes the `helm_frames` row.

**The model's only job is summary generation.** Frame structure, field values, and
`frame_status` all come from the cold frame itself — the model does not infer these.
The summary is the only model-dependent field in the migration.

**Summary prompt:**
```
Summarize what this conversation turn covered in 1-3 sentences.
Be specific. Name the topic, the decision made or question explored, and the outcome.
Return only the summary text. No preamble.

Turn:
User: [user message]
Helm: [helm response]
```

**Write safety rule — delete-after-confirm:**
The `helm_frames` row is deleted only after confirming the `helm_memory` write
succeeded (HTTP 201, no error field in response). On write failure: leave the frame
in `helm_frames` with `layer='cold'`. Log the failure. Return error to caller.
The transient workspace is the safety net — nothing is lost, worst case is delayed migration.

**frame_status preservation:**
The `frame_status` value is read from the `helm_frames` column (authoritative per BA6
Projectionist contract), written into `full_content` JSONB in `helm_memory`. The column
value wins on any conflict.

---

## 12. Helm Prime Integration — Routine 0/4 Updates (BA7f)

**File to modify:** `agents/helm/helm_prompt.md`

### Routine 0 — Session Start (invoke Projectionist setup)

After the SESSION_ID generation step, add:

```markdown
**Runtime connectivity check (T1):**
At session start, confirm the Helm Runtime Service is available:

```bash
curl -s http://localhost:8000/health | python3 -c "
import sys, json
h = json.load(sys.stdin)
print(f'Runtime: {h[\"status\"]}')
for name, check in h.get('checks', {}).get('models', {}).items():
    print(f'  {name}: {check[\"status\"]}')
"
```

If runtime is unreachable: log [RUNTIME-UNAVAILABLE] and continue session.
Projectionist and Archivist invocations will fail gracefully in this session.
Do not block session start on runtime availability.
```

### Routine 0 — Per-turn Projectionist invocation update

Replace the Agent tool invocation with a direct runtime call:

```markdown
**Per-turn — after delivering response to Maxwell:**

```bash
# USER_MSG and HELM_MSG must be set as env vars before this block.
# Content is written to a temp file — handles multiline, quotes, and special characters.
# Same pattern as brain.sh. Inline shell interpolation breaks on real message content.

PROJ_TMPFILE=$(mktemp /tmp/proj_req_XXXXXX.json)
node -e "
  const body = {
    session_id: process.env.SESSION_ID,
    turn_number: parseInt(process.env.TURN_COUNT),
    user_message: process.env.USER_MSG,
    helm_response: process.env.HELM_MSG,
    context: { project: 'hammerfall-solutions', agent: 'helm' }
  };
  process.stdout.write(JSON.stringify(body));
" > "$PROJ_TMPFILE"

curl -s -X POST http://localhost:8000/invoke/projectionist \
  -H "Content-Type: application/json" \
  -d @"$PROJ_TMPFILE"
rm -f "$PROJ_TMPFILE"
```

`USER_MSG` and `HELM_MSG` are set to the verbatim turn content immediately before this
block. Node reads them via `process.env` and handles all escaping via `JSON.stringify`.
Never pass verbatim message content via shell string interpolation.
```

### Routine 4 — Memory Update (invoke Archivist)

Replace the Agent tool invocation with a direct runtime call:

```markdown
**Triggering Archivist for frame migration:**

```bash
curl -s -X POST http://localhost:8000/invoke/archivist \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"turn_number\": $TURN_COUNT,
    \"context\": { \"project\": \"hammerfall-solutions\", \"agent\": \"helm\" }
  }"
```

Archivist queries helm_frames for cold frames and migrates them.
This is a post-response operation. Do not block response delivery on it.
```

**Agent contracts (projectionist.md, archivist.md):**
The T1 execution model note in both files is updated:
- Old: "At T1, executes as a sub-agent spawned by Helm Prime via the Agent tool"
- New: "At T1, receives requests routed from Helm Prime via the Helm Runtime Service
  (`POST /invoke/[role]`). Helm Prime calls the runtime directly via bash curl in
  Routines 0 and 4. The Agent tool is no longer in this invocation path."

---

## 13. Docker Packaging (BA7e)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Design rule:** `--host 0.0.0.0` makes the service accessible from the Docker network.
Port is read from `config.yaml` in development (uvicorn default); `--port 8000` here
matches the config default and can be overridden by the compose file.

### docker-compose.yml

```yaml
version: "3.9"

services:
  helm-runtime:
    build: ./services/helm-runtime
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SUPABASE_BRAIN_URL=${SUPABASE_BRAIN_URL}
      - SUPABASE_BRAIN_SERVICE_KEY=${SUPABASE_BRAIN_SERVICE_KEY}
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      ollama:
        condition: service_healthy
    volumes:
      - ./services/helm-runtime/config.yaml:/app/config.yaml:ro

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  ollama_data:
```

**Notes:**
- `OLLAMA_BASE_URL` is set to `http://ollama:11434` (Docker service name) — not localhost.
  This is the container-to-container path. The config default of `http://localhost:11434`
  is correct for non-Docker local development only.
- Model volumes persist between restarts — Qwen2.5 3B does not re-download on every `up`.
- The runtime waits for Ollama's health check before starting. No manual startup sequencing.

---

## 14. Smoke Test (scripts/smoke_test.sh)

End-to-end validation. All 6 checks must pass. No partial passes.

**Required env vars for smoke test to run:**
```bash
ANTHROPIC_API_KEY          # Helm Prime model calls (BA7 uses stub — verifies config loads)
SUPABASE_BRAIN_URL         # Supabase REST endpoint
SUPABASE_BRAIN_SERVICE_KEY # Archivist writes to helm_memory
OLLAMA_BASE_URL            # defaults to http://localhost:11434 if not set
```

**Test sequence:**

```bash
#!/bin/bash
set -e

BASE_URL="${HELM_RUNTIME_URL:-http://localhost:8000}"
BRAIN_URL="${SUPABASE_BRAIN_URL}"
SERVICE_KEY="${SUPABASE_BRAIN_SERVICE_KEY}"
TEST_SESSION="smoke-test-$(date +%s)"
TEST_TURN=1

echo "== Helm Runtime Smoke Test =="
echo "Runtime: $BASE_URL"
echo "Session: $TEST_SESSION"
echo ""

# Check 1: /health — all configured endpoints reachable
echo "Check 1: /health"
HEALTH=$(curl -sf "$BASE_URL/health")
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [ "$STATUS" != "healthy" ]; then
  echo "FAIL: /health returned $STATUS"
  echo "$HEALTH" | python3 -m json.tool
  exit 1
fi
echo "  PASS: status=healthy"

# Check 2: /invoke/projectionist — valid frame JSON returned
echo "Check 2: /invoke/projectionist — frame JSON"
FRAME_RESPONSE=$(curl -sf -X POST "$BASE_URL/invoke/projectionist" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$TEST_SESSION\",
    \"turn_number\": $TEST_TURN,
    \"user_message\": \"Smoke test user message — BA7 validation\",
    \"helm_response\": \"Smoke test Helm response — BA7 validation\",
    \"context\": {\"project\": \"hammerfall-solutions\", \"agent\": \"helm\"}
  }")
echo "$FRAME_RESPONSE" | python3 -c "
import sys, json
f = json.load(sys.stdin)
assert 'session_id' in f, 'Missing session_id'
assert 'frame_status' in f, 'Missing frame_status'
assert f['frame_status'] == 'active', f'Expected active, got {f[\"frame_status\"]}'
print('  PASS: frame JSON valid, frame_status=active')
"

# Check 3: Frame written to helm_frames in Supabase
echo "Check 3: helm_frames row exists"
FRAMES=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_frames?session_id=eq.$TEST_SESSION&select=id,frame_status" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")
COUNT=$(echo "$FRAMES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "$COUNT" -lt 1 ]; then
  echo "FAIL: No helm_frames row found for session $TEST_SESSION"
  exit 1
fi
echo "  PASS: $COUNT frame(s) in helm_frames"

# Check 4 + 5: Archivist migrates frame to helm_memory and deletes helm_frames row
echo "Check 4+5: /invoke/archivist — migration + delete"
curl -sf -X POST "$BASE_URL/invoke/archivist" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$TEST_SESSION\",
    \"turn_number\": $TEST_TURN,
    \"context\": {\"project\": \"hammerfall-solutions\", \"agent\": \"helm\"}
  }" > /dev/null

# Check helm_frames row is gone
REMAINING=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_frames?session_id=eq.$TEST_SESSION&select=id" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")
REMAINING_COUNT=$(echo "$REMAINING" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "$REMAINING_COUNT" -gt 0 ]; then
  echo "FAIL: helm_frames row not deleted after Archivist migration"
  exit 1
fi
echo "  PASS: helm_frames row deleted"

# Check 6: helm_memory row exists with correct content
echo "Check 6: helm_memory row exists"
MEMORY=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_memory?project=eq.hammerfall-solutions&agent=eq.helm&memory_type=eq.frame&order=created_at.desc&limit=1" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")
MEMORY_COUNT=$(echo "$MEMORY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))")
if [ "$MEMORY_COUNT" -lt 1 ]; then
  echo "FAIL: No helm_memory frame row found"
  exit 1
fi
echo "  PASS: helm_memory row exists"

echo ""
echo "== All 6 checks passed. BA7 smoke test complete. =="
echo ""
echo "NOTE: Clean up test rows from Supabase dashboard:"
echo "  helm_memory WHERE project='hammerfall-solutions' AND content LIKE '%Smoke test%'"
```

---

## 15. PR Sequence

| PR | What | Key Files | Pause |
|---|---|---|---|
| **BA7a** | Service skeleton — FastAPI, LiteLLM, supabase_client.py, middleware scaffold, /health (models + Supabase), /config/agents, request schema, startup env validation | `main.py`, `model_router.py`, `middleware.py`, `supabase_client.py`, `config.yaml`, `requirements.txt` | Yes |
| **BA7b** | Projectionist wired — frame creation on Qwen2.5 3B, Ollama JSON mode, full schema nullable fields, output validation with raw logging | `agents/projectionist.py`, prompt update in `main.py` | Yes |
| **BA7c** | Archivist wired — frame migration on Qwen2.5 3B, summary generation, delete-after-confirm, frame_status preservation | `agents/archivist.py` | Yes |
| **BA7d** | BYO model config layer — `custom` provider type, config schema validation, model swap documentation | `model_router.py` update, `config.yaml` schema, `Dockerfile` | Yes |
| **BA7f** | Helm integration — Routine 0/4 updated to call runtime via Bash curl, Agent tool removed from this path, agent contract T1 notes updated | `agents/helm/helm_prompt.md`, `agents/helm/projectionist/projectionist.md`, `agents/helm/archivist/archivist.md` | Yes |
| **BA7e** | Docker packaging + full end-to-end smoke test (Claude Code → runtime → Supabase path) | `Dockerfile`, `docker-compose.yml`, `scripts/smoke_test.sh` | Yes — all 6 checks must pass |

---

## 16. Success Criteria

| # | Criterion |
|---|---|
| 1 | `docker-compose up` starts cleanly. Only required env vars: `ANTHROPIC_API_KEY`, `SUPABASE_BRAIN_URL`, `SUPABASE_BRAIN_SERVICE_KEY`. No manual config beyond these. |
| 2 | `GET /health` returns `status: healthy` with all configured model endpoints and Supabase confirmed reachable. |
| 3 | `POST /invoke/projectionist` returns valid frame JSON. Frame row written to `helm_frames`. |
| 4 | `POST /invoke/archivist` migrates the cold frame to `helm_memory` at full fidelity. `helm_frames` row deleted. |
| 5 | Swapping Projectionist from `qwen2.5:3b` to any other model requires exactly one `config.yaml` line change and a service restart. No code changes. |
| 6 | Smoke test passes end-to-end on the full path: Claude Code → runtime → Supabase. All 6 checks pass. |
| 7 | A missing required env var at startup produces a clear named error — not a silent failure or a crash at request time. |

---

## 17. What BA7 Does Not Build

These are explicitly out of scope. They are noted here to prevent scope creep during
implementation and to give them a clear home in future build areas.

| Item | Future Build Area |
|---|---|
| Prime Directives guard (runtime middleware) | BA9 |
| Personality injection (runtime middleware) | BA8 |
| Speaker wired to runtime | Stage 1 / BA10+ |
| **Speaker session initialization** — brain reads for `helm_personality` and `helm_beliefs` at T3 session start (persistent process, 4090 node). Speaker must load personality and beliefs before the first request is routed to it. Without this, Speaker at T3 responds as a blank model, not as Helm. | Stage 4 / Speaker wiring build area |
| pgvector semantic search on frames | Stage 1 |
| Quartermaster — user management, billing, product surface | Stage 2 |
| Helm Cloud deployment (actual cloud infra) | Stage 4 |
| Tasker dynamic instantiation | Stage 4 |
| Multi-user session isolation | Stage 2+ |
| Rate limiting, auth middleware | Stage 2+ |

---

## 18. Dependencies

**Required installed locally before BA7a can run:**
- Python 3.11+
- `pip install litellm fastapi uvicorn httpx pyyaml`
- Ollama with `qwen2.5:3b` pulled: `ollama pull qwen2.5:3b`

**Required env vars:**
```bash
ANTHROPIC_API_KEY=...
SUPABASE_BRAIN_URL=https://zlcvrfmbtpxlhsqosdqf.supabase.co
SUPABASE_BRAIN_SERVICE_KEY=...
OLLAMA_BASE_URL=http://localhost:11434   # optional — defaults to this
```

**Supabase tables required (already exist from BA6):**
- `helm_frames` — created in BA6d migration
- `helm_memory` — created in B1 migration

---

*Canonical source: `docs/ba7-spec.md`*
*Maintained by Core Helm. Implementation follows this spec exactly. Deviations require Maxwell approval.*
