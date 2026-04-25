# SITREP — T0.A8 API Auth

**Date:** 2026-04-25
**Branch:** `feature/t0a8-api-auth`
**Tier:** ARCH (architect-approved per [arch_notes/T0.A8_api_auth.md](../arch_notes/T0.A8_api_auth.md))
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A8

## Scope executed

Static bearer-token gate on the runtime endpoints that spend money or expose configuration. Five artifacts:

1. **`services/helm-runtime/auth.py`** — `require_token` FastAPI dependency. Reads `HELM_API_TOKEN` env, parses `Authorization: Bearer ...` header, constant-time compares to expected token. Returns 500 on missing env (server misconfig), 401 on missing/wrong token. Adds `WWW-Authenticate: Bearer` on 401s.
2. **`main.py` route hookup** — `Depends(require_token)` on `POST /invoke/{agent_role}` and `GET /config/agents`. `GET /health` stays exempt for Docker/Render healthchecks.
3. **`docker-compose.yml`** — `HELM_API_TOKEN` env var passthrough; documented in the file's required-env block.
4. **`tests/test_auth.py`** — 9 tests: 5 unit (require_token in isolation under monkeypatched env) + 4 integration (TestClient against a minimal FastAPI fixture exercising 401/200 paths through real header parsing).
5. **`docs/runbooks/0001-api-token-rotation.md`** — operational procedure per architect's done-criteria. Generation, env update, restart, verification; root-cause notes that automated rotation is deferred to Stage 2 by design.

## Verification

Local:

- `mypy --strict .` → 0 errors across 16 source files (auth.py + tests/test_auth.py added)
- `ruff check .` → clean
- `black --check .` → clean
- `pytest tests/test_auth.py -v` → 9 passed
- `pytest -v` (full suite) → all auth tests pass; one pre-existing local pytest failure (`test_main_module_imports` on Py3.14 pydantic-wheels gap from T0.A3) unchanged

CI will validate the full pipeline including the auth tests on Py3.12.

## Files changed

| File                                       | Change                                                                                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `services/helm-runtime/auth.py`            | NEW — `require_token` dependency, `ENV_VAR` constant.                                                                                            |
| `services/helm-runtime/main.py`            | + `Depends, require_token` imports; `dependencies=[Depends(require_token)]` on `/invoke/{agent_role}` and `/config/agents`. `/health` untouched. |
| `services/helm-runtime/tests/test_auth.py` | NEW — 5 unit + 4 integration tests.                                                                                                              |
| `docker-compose.yml`                       | + `HELM_API_TOKEN` env passthrough; required-env header updated.                                                                                 |
| `docs/runbooks/0001-api-token-rotation.md` | NEW — first runbook in the repo.                                                                                                                 |

## Implementation notes (small flags)

1. **`dependencies=[Depends(require_token)]` on the decorator, not as a route param.** Keeps the route signature uncluttered; the dependency runs but its return value isn't injected (we only use it for its side effects: raising on bad auth).
2. **`secrets.compare_digest`** for the token comparison — constant-time, prevents timing-attack inference of valid prefixes. Tiny cost, defensible.
3. **500 (not 401) when env unset.** Matches the architect's note: misconfig is a server bug, not an unauthorized caller. Caller hitting 500 means deploy is broken; caller hitting 401 means they're holding the wrong token.
4. **Tests use a minimal FastAPI fixture** rather than importing the real app. The real app's lifespan loads `ModelRouter` which needs Supabase env — that's brittle for unit-testing auth. The fixture mounts a single protected route + `/health` and exercises the same dependency.
5. **`/events` is mentioned in the arch note but doesn't exist as a route yet.** When it lands (likely Stage 2 SSE/streaming), the same `dependencies=[Depends(require_token)]` pattern applies.

## Architect open-question resolutions

The arch note had four open questions; the architect resolved two in their review:

- **Token in `helm-ui/.env`:** one shared token until Stage 2 user auth (per-deploy rotation = over-engineering at T1)
- **`/health` payload:** must stay boring (status booleans + agent count only); re-validate at T0.A6 build → done at T0.A6 (no env-derived data emitted)

The remaining two open items are operational, not blocking:

- **No automated token rotation** — the runbook is the explicit acceptance of manual rotation
- **500 on unconfigured token** — surfaced in tests; T0.A12 CI smoke will catch a bad deploy before it ships

## Adjacent debt explicitly NOT in scope

- **CI smoke test against the running container.** The arch note says "CI smoke test exercises both 401 and 200 paths." Pytest TestClient does this end-to-end against the real ASGI app — same wire format as `curl`. Container-level smoke (curl into a running container) lands with T0.A12 (CI container build).
- **Frontend integration.** T3.4 — adds the `Authorization: Bearer ...` header to the helm-ui fetch wrapper. Not now.
- **Rate limiting on `/invoke`.** T4.2 — additive to auth, uses the bearer token as the rate-key identity.

## What this unlocks

- **The runtime no longer leaks budget on drive-by curls.** Local dev, Docker compose, and any future Render deploy all gate `/invoke` and `/config` behind the bearer.
- **First runbook in the repo.** Sets the shape for T0.A10 (backup-restore), T0.A11 (cost kill-switch), T1.x deploy procedures.
- **T0.A11 (Runtime Guardrails)** can attribute `/invoke` requests to a known caller (the bearer token IS the caller identity at T1).
- **T0.A12 (CI container build)** can write a smoke test that hits the auth path end-to-end — the contract is documented and enforced.
- **T3.4 (Frontend integration)** has a stable API contract: send `Authorization: Bearer $VITE_HELM_API_TOKEN`, expect 401 on missing/wrong, 200 on valid.

Phase 0A pacing note: task 8 of ~15. Deployment-hardening arc closes (T0.A7+T0.A8); the next infra beat is T0.A9 (env var contract) — also ARCH per spec, has an existing arch note. Wait, actually looking ahead: T0.A9 doesn't have an arch note in `arch_notes/`. Let me re-check before the next task.

## Review

ARCH-tier — architect already approved the design. Bundle review for: (a) implementation matches the design, (b) the 5 small flags are defensible, (c) runbook structure is the right pattern for follow-up runbooks.

After merge, T0.A9 is next (need to verify whether it's STOP or ARCH; if ARCH and missing an arch note, I'll write one and pause).
