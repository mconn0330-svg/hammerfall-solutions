# SITREP — T0.A6 Observability Foundation

**Date:** 2026-04-25
**Branch:** `feature/t0a6-observability-foundation`
**Tier:** STOP (sets the logging shape for everything after)
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A6 (lines 447–535)

## Scope executed

T0.A6 lays the observability convention before T0.B1 (memory module) lands. Three artifacts:

1. **`services/helm-runtime/observability.py`** — structlog configuration, correlation-ID context var, OpenTelemetry tracer (no exporter).
2. **`main.py` correlation middleware** — every request binds a `correlation_id` (from incoming `x-correlation-id` header or freshly generated UUID); auto-attached to every log line in the request scope; echoed back in the response.
3. **`AGENTS.md` hard rule 6** — flesh-out from "use structlog with helm.<module> names" to the full convention: event naming, error fields, level semantics, span instrumentation, and the stdlib bridging story.

## Files changed

| File                                     | Change                                                                                                                                                                                                    |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/helm-runtime/observability.py` | NEW — `configure_logging()`, `get_logger()`, `correlation_id_var`, `get_correlation_id()`, `new_correlation_id()`, `tracer`.                                                                              |
| `services/helm-runtime/requirements.txt` | + `structlog==25.5.0`, `opentelemetry-api==1.41.1`, `opentelemetry-sdk==1.41.1`.                                                                                                                          |
| `services/helm-runtime/main.py`          | `configure_logging("info")` at module load; `correlation_middleware` registered as FastAPI HTTP middleware; imports `Request`/`Response`/`Awaitable`/`Callable`/`structlog` for the middleware signature. |
| `AGENTS.md`                              | Hard rule 6 expanded with the full convention (events, fields, levels, spans, stdlib bridging).                                                                                                           |

## Design decisions worth flagging

**Stdlib `logging` is bridged, not replaced.** Existing modules (`main.py`, `middleware.py`, agents/, etc.) currently use `logging.getLogger(__name__)`. Rather than refactoring 7+ files in this PR, `configure_logging()` installs a `structlog.stdlib.ProcessorFormatter` so stdlib log records flow through the same JSON pipeline. They get `correlation_id`, timestamp, level, traceback for free. New modules should prefer `observability.get_logger()` for the ergonomic `log.info("event.name", key=value)` API; the migration of existing callers can happen incrementally as files are touched (per "clean adjacent debt as you go").

**OpenTelemetry tracer with no exporter.** `tracer = trace.get_tracer("helm.runtime")` returns a working tracer using the SDK's default tracer provider. Spans run, attributes attach, parent/child relationships hold — but nothing ships off-process because no exporter is configured. This matches the spec exactly: "spans are just structured. T4 / Stage 2 wires an exporter when there's a place to send them."

**Correlation ID propagation.** The middleware accepts an inbound `x-correlation-id` header (so Render → runtime, or Claude Code → runtime, can stitch traces across hops) and falls back to a fresh UUID. The ID is bound via `structlog.contextvars` so every log in the async task tree picks it up automatically. Cleared in `finally` so background tasks don't leak the ID into the next request.

## Verification

Local:

- `mypy --strict .` → 0 errors across 14 source files (observability.py added)
- `ruff check .` → clean
- `black --check .` → clean
- `pytest` → 2/3 pass (1 local failure is the Py3.14 pydantic-wheels gap from T0.A3, unchanged)

CI will validate on this PR.

## Spec deviations

None. Three implementation choices to flag:

1. **`StackInfoRenderer` added to the processor chain.** The spec lists `merge_contextvars / add_log_level / TimeStamper / dict_tracebacks / JSONRenderer`. I added `StackInfoRenderer` between `TimeStamper` and `dict_tracebacks` — it lets call sites pass `stack_info=True` to surface a stack trace on non-error events too. Diagnostic value, no operational cost.

2. **Pinned versions, not floor versions.** Spec says `>=24.0.0` / `>=1.25.0`. T0.A2 set the precedent of pinning for reproducibility (CI matches local matches pre-commit). Pinned to current latest: `structlog==25.5.0`, `opentelemetry-{api,sdk}==1.41.1`. Bumps via deliberate PR.

3. **Module-level `configure_logging("info")` instead of inside `lifespan`.** Spec's example code shows the middleware in `main.py` but doesn't specify _when_ `configure_logging()` runs. Putting it at module load (before `lifespan`) means startup logs (config loading, ModelRouter init, etc.) are JSON-shaped from the very first line. Inside `lifespan` would lose those.

## Adjacent debt explicitly NOT in scope

- **Migrating existing `logging.getLogger(__name__)` callers to `observability.get_logger()`.** Stdlib bridging means they Just Work. Migration is an aesthetic improvement (kwargs API), not a behavior change. Per the "clean adjacent debt as you go" rule, this happens when those files are touched for other reasons.
- **Adding `tracer.start_as_current_span()` calls into existing handlers.** The tracer is _available_; instrumentation lands as part of the operations it wraps (memory writes in T0.B1, agent invocations as they're touched). No instrumentation in this PR — that would be gold-plating.

## What this unlocks

- **T0.B1 (Memory Module Core)** lands fully observable from day one. Every `memory.write()` gets a span, every log line carries the correlation ID.
- **AGENTS.md hard rule 6** is now mechanically achievable, not aspirational. Future contributors have the recipe.
- **Cross-component request tracing** — when Claude Code → Render → runtime → Supabase, the same `x-correlation-id` flows through (once each hop honors it).

Phase 0A pacing note: task 6 of ~15. Type-discipline arc closed (T0.A5); observability arc opens here. Next infra beat is T0.A7 (deployment hardening, ARCH-tier — needs an arch-notes one-pager before build starts).

## STOP gate

Standing by for your explicit approval. After merge, T0.A7 is next — but it's ARCH-tier, so it needs a one-pager in `docs/stage1/arch_notes/` and architect review before any build PR.
