# AGENTS.md — Operating Contract for Agents in This Repo

This file is the canonical, vendor-neutral instruction set for any agentic coding tool working in `hammerfall-solutions`. It is picked up natively by Claude Code, Cursor, Aider, Codex, and other tools that follow the emerging `AGENTS.md` convention. Do not branch this file by vendor; if a tool requires its own filename, add a one-line shim that points here.

## What this repo is

Hammerfall is the runtime + UI for Helm — an ambient AI presence Maxwell McConnell is building. T1 (the first launchable Helm) is currently being built per `docs/stage1/Helm_T1_Launch_Spec_V2.md`. That document is **canonical** for T1 work; if anything in this file conflicts with V2, V2 wins.

## Hard rules

1. **V2 spec is canonical.** When in doubt about scope, intent, or shape, read `docs/stage1/Helm_T1_Launch_Spec_V2.md` first. ARCH-tier tasks have additional design notes in `docs/stage1/arch_notes/`.

2. **Conventional Commits required.** Every commit message follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). `commitlint` enforces this locally (T0.A2) and in CI (T0.A4). Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`. Allowed scopes: `memory`, `runtime`, `ui`, `agent`, `prompt`, `infra`, `ci`, `docs`, `migration`, `repo`, `auth`, `obs`, `ops`. Plus `deps` / `deps-dev` for Dependabot's automated PRs. See `commitlint.config.js`.

3. **STOP gates are non-optional.** Any task tagged `STOP` in the V2 spec requires Maxwell's explicit approval before merge. Any task tagged `ARCH` requires the architect's approval of the matching one-pager in `docs/stage1/arch_notes/` before build starts. Do not relabel mid-build to skip a gate.

4. **Tests come with the code.** New code lands with tests. The test harness exists (T0.A3 → pytest for Python, vitest for JS). If you add behavior, add a test. If you fix a bug, add a regression test. T2.9 is the behavioral regression net for the runtime; bug repros land there as `tests/simulations/<scenario>.yaml`.

5. **Memory writes go through `memory.write()`.** Never call `supabase_client.insert/post` directly from agent code. Never invoke `brain.sh` (deleted at T0.B6 — references in any new code are a regression). Reads documented in T0.B3's disposition table; some still go through `read_client.py` (renamed at T0.B6) until Stage 2.

6. **Structured logging convention.** Use `structlog` via `observability.get_logger()` (T0.A6). Logger names follow `helm.<module>` (`helm.memory`, `helm.runtime`, `helm.agent.contemplator`). Event names use `dotted.snake_case` (`memory.write`, `memory.write.failed`, `agent.invoked`). Every event carries `correlation_id` (auto-bound from the FastAPI middleware). Error events include `error` (str), `error_type` (cls name), and traceback. Levels: `info` for normal events, `warning` for recoverable issues, `error` for failures, `critical` for things that should page. Logs are JSON-shaped — no `print()` statements in shipped code. Stdlib `logging.getLogger(__name__)` is bridged through the same processor pipeline so existing callers Just Work; new code should prefer the structlog API for ergonomic kwargs. Span instrumentation: wrap cross-component operations with `tracer.start_as_current_span("name")` (no exporter in T1; spans are structured for in-process inspection only).

7. **Don't claim a PR is ready until CI is green.** "Looks good locally" is not sufficient. CI exists for this reason (T0.A4 onward).

## Soft rules — strong defaults

- **Single-dev sequential execution.** One PR at a time. No parallel branches without explicit reason.
- **Each PR opens with a SITREP** in `docs/stage1/SITREPs/`. Cite the matching task ID(s); flag out-of-scope items so they're not lost.
- **Founding docs stay global.** `docs/founding_docs/` is the canonical reference. Update there before referencing in spec or PR.
- **Clean adjacent debt as you go.** If you touch a file or area and notice something broken — a typo, a dead variable, a small lint error, a stale comment, an obsolete reference — fix it in the same PR rather than filing a Finding. Accumulated debt is worse than a slightly larger diff; the "I'll come back to it" PR rarely materializes. Two boundaries: (a) the cleanup must be in code you're already editing or directly adjacent — don't go hunting for unrelated dirt across the repo; (b) new _features_ still go through Maxwell — V2 is the floor and ceiling for T1 features. Cleanup of code under your hands is welcomed and expected; new scope is not.
- **Found a problem outside the current task's adjacency?** If it's _not_ in code you're already touching (a different module, a feature you'd have to go looking for), append to `docs/stage1/Post_T1_Findings.md` with a Finding #NNN block and reference it in the PR's SITREP. The Findings queue is for genuinely-out-of-scope discoveries, not for "I noticed this while I was here" — those get fixed in flight per the rule above.

## Testing conventions

- **Python tests live in `services/helm-runtime/tests/`** mirroring the module under test (memory module → `tests/test_memory_writer.py`). Run via `pytest` from the service dir. `pytest-asyncio` is in `auto` mode — async test functions need no decorator.
- **JS/JSX tests are `*.test.jsx` co-located with their components** (e.g. `src/components/HelmNode.jsx` → `src/components/HelmNode.test.jsx`). Bare smoke tests live in `src/__tests__/`. Run via `npm test` from `helm-ui/`.
- **New code lands with tests.** PR template enforces. Bug fixes land with a regression test that fails before the fix.
- **One assertion per test where practical.** Multiple assertions are fine when they describe the same observation; split when they describe distinct behaviors.
- **Tests do not hit external services.** Use the `supabase_stub` fixture from `services/helm-runtime/tests/conftest.py` for any code path that would otherwise call Supabase. Real-Supabase tests belong behind a marker we have not introduced yet.
- **Coverage targets** (per V2 spec §T0.A3): 80%+ for the memory module + Tier 2 brain types (T0.B1–T0.B7), 60%+ for runtime additions, smoke + critical-path only for UI integration.

## Where to look for known failures

`docs/runbooks/` — symptom → diagnosis → fix → root cause. If you hit something that should have a runbook and doesn't, add one (template at `docs/runbooks/0000-template.md`).

## When in doubt

Ask Maxwell. He's the sole human stakeholder; surfacing uncertainty early is cheaper than rebuilding work later.

---

**Maintenance:** This file is updated as the operating contract evolves (new conventions, new gates, etc.). Treat updates as ARCH-tier even though no `arch_notes/` one-pager exists for it — changes here ripple through every future contributor's behavior.
