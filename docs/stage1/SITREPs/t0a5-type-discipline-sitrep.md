# SITREP — T0.A5 Type Discipline + ADR-001

**Date:** 2026-04-25
**Branch:** `feature/t0a5-type-discipline`
**Tier:** STOP (ADR-001 sets Phase 1 trajectory)
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A5 (lines 428–443)

## Scope executed

T0.A5 has two distinct deliverables — Python type discipline (executed) and a JS path decision (recorded as ADR-001). Both land here, and the deferred mypy step from T0.A4 (PR #103) gets re-enabled in CI.

### Python side — mypy strict on helm-runtime

Every signature in `services/helm-runtime/` is now typed. `mypy --strict` reports 0 errors across 13 source files.

Path:

- Added `mypy` + `types-PyYAML` to `requirements-dev.txt`
- Added `[tool.mypy]` block to `pyproject.toml` with `strict = true`, `python_version = "3.12"`, `plugins = ["pydantic.mypy"]`
- Override `litellm.*` (no stubs) — `ignore_missing_imports = true`
- Walked the codebase and typed every signature, every return path, every container

The pass surfaced and fixed:

- All `dict` / `list` / `tuple` generics now have type arguments (43 → 0)
- All `Returning Any from function declared to return X` resolved by typed local variables (17 → 0)
- 4 implicit-Optional defaults converted to explicit `X | None = None`
- 6 module-level globals in `main.py` (`router`, `supabase`, etc.) declared as `X | None` with `assert ... is not None` narrowing at each use site (mypy's standard pattern for late-init globals)
- 1 FastAPI signature reordered (`body: InvokeRequestBody` first, `agent_role: str` with `FastAPIPath()` second) so mypy stops complaining about `EllipsisType` defaults
- 1 endpoint return type widened to `InvokeResponse | JSONResponse` (the directive-violation path returns JSONResponse)
- `lifespan` annotated with `AsyncIterator[None]`
- `_generate_summary` got the unreachable `return None` after the retry loop (mypy's flow analysis required it)
- Provider StrEnum + 4× `from e` exception chaining were already done in T0.A4's adjacent cleanup

### JS side — ADR-001 recorded, conversion deferred to T1.5b

`docs/adr/0001-typescript-conversion-for-helm-ui.md` records the decision: **Path A** (full TSX conversion), bundled with T1.5b (design-token application). The spec recommends Path A; this ADR captures both the decision and the rejected alternative (Path B: JSDoc + ESLint strict) so future contributors don't re-litigate.

T0.A5 does **not** perform the conversion. T1.5b touches every component anyway; converting at the same time means one diff per file instead of two.

### CI re-enabled mypy step

`.github/workflows/ci.yml` now runs `mypy .` after lint and before test. The "deferred to T0.A5" comment in the workflow is replaced with a note that the step is live. Branch protection (which Maxwell will set post-merge per T0.A4) will require this step green.

## Files changed

| File                                                 | Change                                                                                                         |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `services/helm-runtime/pyproject.toml`               | `[tool.mypy]` block + pydantic plugin + litellm override                                                       |
| `services/helm-runtime/requirements-dev.txt`         | + `mypy==1.20.2`, + `types-PyYAML==6.0.12.20260408`                                                            |
| `services/helm-runtime/main.py`                      | Globals → `X \| None`, asserts at each use site, AsyncIterator return, signature reordering, return-type union |
| `services/helm-runtime/middleware.py`                | `dict` / `list` generics, explicit Optional default for `messages`                                             |
| `services/helm-runtime/model_router.py`              | All dict/list returns typed; cached health-result narrowed via typed local                                     |
| `services/helm-runtime/supabase_client.py`           | `dict[str, Any]` everywhere; embedding `list[float]`; typed locals to convert Any returns                      |
| `services/helm-runtime/embedding_client.py`          | (already clean)                                                                                                |
| `services/helm-runtime/agents/archivist.py`          | results dict typed; payload signatures typed; unreachable `return None` for retry loop                         |
| `services/helm-runtime/agents/contemplator.py`       | snapshot list parameters typed; `_extract_json` typed locals; `_fetch_snapshot` tuple                          |
| `services/helm-runtime/agents/helm_prime.py`         | typed local for `response`                                                                                     |
| `services/helm-runtime/agents/projectionist.py`      | `last_exc: Exception \| None`                                                                                  |
| `services/helm-runtime/tests/conftest.py`            | `_SupabaseStub` interface fully typed                                                                          |
| `services/helm-runtime/tests/test_smoke.py`          | `supabase_stub: Any` parameter annotation                                                                      |
| `.github/workflows/ci.yml`                           | + mypy step                                                                                                    |
| `docs/adr/0001-typescript-conversion-for-helm-ui.md` | NEW — Path A decision recorded                                                                                 |

## Spec deviations

None. T0.A5 deliverables met:

- Python: `mypy --strict` clean ✓
- Type stubs for libraries that need them (PyYAML; litellm overridden because no stubs ship) ✓
- JS: ADR-001 documents the decision, the rejected path, and the rationale ✓

## Adjacent debt

Per the new "clean adjacent debt as you go" rule, there were small adjacent items I did NOT fix because they're not actually adjacent to "make mypy strict pass" (different code path, different concern):

- **The 1 local pytest failure** — `test_main_module_imports` still fails on Maxwell's Py3.14 because pinned `pydantic==2.11.3` has no Py3.14 wheels. CI uses Py3.12 (per V2 §T0.A4), where it passes. This is the same well-known local-vs-CI gap noted in T0.A3 SITREP. Bumping the pin is its own deliberate decision; not in scope here.
- **No new tests** — type discipline by itself doesn't change behavior, so no regression test surface. Tests will arrive with T0.B1 onward as actual logic lands.

## What this unlocks

- **AGENTS.md hard rule 4 ("tests come with the code")** combines with strict typing for the runtime — every new function lands typed, every new branch covered. No untyped escape hatches.
- **T0.B1 (Memory Module Core)** — the next ARCH-tier task — lands in a fully-typed environment. The memory module's interface contract gets compile-time enforcement from day one.
- **T1.5b (UI design-token application)** — when this lands, the TSX conversion happens alongside. ADR-001 is the prior decision the PR cites.
- **CI now enforces type safety on every PR.** Once Maxwell sets branch protection (T0.A4 post-merge step), no PR with a type error can merge.

Phase 0A pacing note: task 5 of ~15. Rules-and-enforcement arc is closed (T0.A1–A4); type-discipline arc opens here. Next infra beat is T0.A6 (observability foundation).

## STOP gate

ADR-001 is the artifact requiring your sign-off — the decision sets Phase 1's frontend trajectory. The mypy strict pass is the runtime contract that subsequent tasks build under. Both want explicit approval before merge.

After approval + merge, T0.A6 (structured logging convention + correlation IDs) starts immediately.
