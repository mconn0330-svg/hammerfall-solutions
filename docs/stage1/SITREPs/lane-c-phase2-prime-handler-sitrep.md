# SITREP — Lane C Phase 2: Prime Handler

**Date:** 2026-04-21
**Branch:** `feature/lane-c-phase2-prime-handler`
**Phase:** Lane C, Phase 2, Tasks 2.1–2.4
**Spec:** `docs/stage1/refounding-ba.md`

## Scope executed

Built the real `_handle_helm_prime` handler to replace the `[STUB]` that `main.py` returned on invoke. Speaker is intentionally NOT removed — both handlers coexist through Phase 2 to prevent a personality-injection regression window. Speaker dies in Phase 3.

## Files created

- `services/helm-runtime/agents/helm_prime.py` — Prime handler. Loads `helm_prompt.md` as base system prompt, injects `helm_personality` scores from Supabase, appends operational context (surface, tier, session metadata), invokes the configured Prime model via `model_router`.

## Files modified

- `services/helm-runtime/main.py` — added `from agents import helm_prime as helm_prime_agent` import; replaced the `_handle_helm_prime` stub with `return await helm_prime_agent.handle(req, router, supabase)`.
- `docker-compose.yml` — added volume mount `./agents/helm/helm_prompt.md:/app/agents/helm/helm_prompt.md:ro` so the handler can read the prompt at runtime without an image rebuild on every edit.

## Spec deviations (documented)

1. **Imports adapted to match actual codebase.** Spec template imported `InvokeRequest` from `agents`; real location is `middleware`. Spec template used `supabase.get()`; real method is `supabase.select()`. Spec template returned `response` directly from `router.invoke()`; real shape is a LiteLLM response where the content is at `result.choices[0].message.content`. Changes tracked in the handler file; behavior matches spec intent.

2. **`PROMPT_PATH` computation: 2 parents, not 4.** Spec template had four `.parent` calls, which assumes the host repo layout. Inside the container (the only place the handler runs), `__file__` is `/app/agents/helm_prime.py` — two `.parent` calls reach `/app`, which is the correct base. Four parents would land at `/` and miss the file. Verified in-container: `PROMPT_PATH` resolves to `/app/agents/helm/helm_prompt.md`, `exists: True`, `size: 45272`.

3. **Added volume mount for `helm_prompt.md`.** Spec's handler design requires the file to be readable at runtime. Without the mount, the handler would raise `RuntimeError` on every invoke (Dockerfile only `COPY`s `services/helm-runtime/*`, and only `config.yaml` was mounted). Tiny infrastructure addition; alternative was shipping the handler broken. Pre-authorized by Max before commit.

4. **Model version NOT bumped.** Spec suggested `claude-opus-4-7 # or current Opus model`. Config retains `claude-opus-4-6` per Max's explicit direction.

## Verification

- **Handler imports correctly inside container** — `from agents.helm_prime import PROMPT_PATH` succeeds, path resolves to the mounted file.
- **`config.yaml` Pydantic validation** — passes; `helm_prime` entry unchanged (provider: anthropic, model: claude-opus-4-6, api_key_env: ANTHROPIC_API_KEY).
- **Runtime boots cleanly** — `docker-compose up -d --build` comes up, ollama reports `Healthy`, helm-runtime starts.
- **`/health` result:**
  - `service: ok`
  - `helm_prime: ok` (Anthropic claude-opus-4-6)
  - `projectionist: ok` (qwen3:4b)
  - `archivist: ok` (qwen3:14b)
  - `contemplator: ok` (qwen3:14b)
  - `supabase: ok` (helm_frames queryable)
  - `speaker: unreachable` (qwen3:8b not pulled — by design, Speaker dies in Phase 3)
  - Overall `status: degraded` — solely due to Speaker's unpulled model. Expected. All four agents in the post-Phase-3 roster are green.
- **Stack tears down cleanly** — `docker-compose down` completes without errors.

## Deferred

**End-to-end invocation test is deferred** to post-Lane-B integration. No UI exists today to drive `POST /invoke/helm_prime`. The handler's code path is verified statically (imports, prompt load, config validation) but not exercised over HTTP end-to-end. This matches the spec's Phase 2 close validation criteria (boot + imports + visual review), which do not require live invocation.

## Noticed but out of scope — AAR candidates

1. **Long-term: `helm_prompt.md` belongs in Supabase.** The volume-mount approach is correct for T1 local dev but brittle for T3 cloud deployment (Hammerfall Cloud can't mount host paths). Prime's identity is brain content, not infrastructure — same trust model as `helm_personality`, which is already loaded from Supabase at runtime. Path forward: `helm_prompt` table (single row vs chunked vs versioned), snapshot mechanism mirroring `brain.sh`/`snapshot.sh`, handler reads Supabase with `.md` fallback. Being spec'd as its own initiative per Max's direction; not a Phase 2 concern.

2. **Stale stub comment in `main.py` `_handle_speaker` docstring** — references "Qwen2.5 3B" as Speaker's model at T1. Current config has Speaker on qwen3:8b. Low-priority; Speaker dies in Phase 3 anyway.

3. **Speaker still uses Opus 4.6 in its embedded `HELM_PRIME_RUNTIME_PROMPT`** — the fallback prompt Speaker sends when escalating to Prime. Duplicates some identity language that's now in `helm_prompt.md`. Redundant-but-not-broken during Phase 2 coexistence; goes away with Speaker in Phase 3.

4. **Personality block uses `/10` formatting** (carried over from Speaker's `_load_personality_block` for consistency). Scores in Supabase are stored 0.0–1.0; the `/10` rendering is a presentation choice. If helm_prompt.md's new "Personality tuning" section (Phase 2 Task 2.5) establishes a different convention, revisit.

## Next

- Merge this PR (STOP for Max review).
- Proceed to Task 2.5: rewrite `helm_prompt.md` under JARVIS-first framing (new branch `feature/lane-c-phase2-prompt-rewrite`).
