# Helm T1 Launch — Consolidated Build Specification V2

| | |
|---|---|
| **Status** | 🟡 Active — supersedes Helm_T1_Launch_Spec.md (v2.0) |
| **Version** | V2 — comprehensive foundation rewrite |
| **Authored** | 2026-04-24, Claude Opus 4.7 (Helm IDE) under Maxwell's planning + architecture authority grant |
| **Purpose** | Land T1 on-demand presence on a production-grade foundation. Memory infrastructure, repo operating contract, test harness, CI, observability, deployment hardening, API auth, cost guardrails, and backup discipline all in place before T1 closes. |
| **Estimated PRs** | 49–57 |
| **Execution model** | Single dev (Helm IDE / me), sequential, methodical. Maxwell reviews. Architect consulted on STOP-gated tasks. |
| **Exit criteria** | A user opens the UI, talks to Helm, sees live agent activity, experiences a coherent identity — on real data, no mocks — running on a stack that has tests, CI, structured logs, traces, an auth boundary, a backup, and a runbook for every known failure mode. |

---

## Why V2 Exists

The v1 spec was correct in shape: T0 memory foundation, freestanding UI work in parallel, Phase 2 backend, Phase 3 integration. Reviewing it after the T0 architecture pivot surfaced a deeper class of issues that v1 did not address:

1. **Spec gaps in T0 itself** — JSONL outbox concurrency race, narrow `MemoryType` enum, dual-write transaction safety, em-dash unicode coupling, missing observability on circuit breaker state changes, four prompt/doc files (`agents/helm/helm_prompt.md`, `archivist.md`, `contemplator.md`, `management/COMPANY_BEHAVIOR.md`) and the docstring at `services/helm-runtime/supabase_client.py:7-11` all encoded the brain.sh paradigm and were not in T0.6's deletion scope.
2. **No repo operating contract** — no `AGENTS.md`, no Conventional Commits enforcement, no ADR template, no runbook directory. The spec v2.0 itself was committed under the message "Update print statement from 'Hello' to 'Goodbye'" (commit `7e771b0`). That is a process failure in the substrate, not a typo.
3. **No test foundation** — zero pytest/vitest config in repo. T1.7 is a hard contract gate that no test will catch when it drifts.
4. **No CI** — every PR relies on Maxwell's manual review. With 35+ PRs ahead and a single dev driving them, that's not sustainable.
5. **No observability beyond `print`** — no structured logging convention, no trace IDs, no correlation IDs across the SSE-runtime-Supabase chain. Debug surface is bash + grep + read the screen.
6. **No deployment hardening** — Dockerfile builds as root, no HEALTHCHECK, no version pins on the base image, no `.dockerignore`. Compose stack is intermittently up.
7. **No API auth** — `/invoke/helm_prime` is open. Acceptable on `localhost`. Not acceptable when T2/T3 reach for ambient.
8. **No backup discipline** — Supabase brain has no documented backup procedure. A single bad RLS migration loses everything.
9. **No cost guardrails** — embedding calls are unmetered. A loop bug burns API budget silently.

V2 layers all of this in. The shape stays — Memory Foundation first, UI in parallel, backend after, integration last. What changes is Phase 0 grows from 6 tasks to 17, a new Phase 4 (Operational Readiness) closes the spec, and every existing task gets the fixes from the spec gap analysis.

---

## Document Status

V2 supersedes `docs/stage1/Helm_T1_Launch_Spec.md` (v2.0). After V2 merges:

- v1 is archived in place — left as the historical artifact, not deleted, with a banner header pointing here.
- All future PRs reference V2 task IDs (e.g., "implements T0.B3").
- If something in V2 is wrong, fix it in V2. Do not edit v1.

---

## Single-Dev Execution Model

This spec assumes one dev (Helm IDE) executes all tasks sequentially, pausing at every STOP gate for Maxwell review. Architect is consulted only on tasks marked **Architect Review**. There is no parallel work, no merge conflicts between dev streams, no coordination cost beyond Maxwell's review cadence.

**Operational implication:** velocity is bounded by review throughput, not by build throughput. The plan is structured so that every batch can be reviewed in ≤30 min by Maxwell.

**STOP gate discipline (V2):**

| Tier | When | Behavior |
|---|---|---|
| **Full STOP — Architect + Maxwell** | Architectural decisions, schema changes, API contracts | PR opens with `[ARCH]` prefix. Architect comments. Then Maxwell reviews + merges. |
| **STOP — Maxwell only** | Behavior changes, agent prompt changes, runtime logic | PR opens with full description. Maxwell reviews + merges. |
| **Batch — Maxwell-only review queue** | Mechanical changes, cosmetics, doc edits | PR opens with `[BATCH]` prefix. Maxwell reviews in groups. |

Every PR description follows the template in **Appendix A — PR Description Template**.

---

## Conventional Commits — Enforced

All commits land under the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) spec. T0.A1 lands a `commitlint` config + git hook that rejects non-compliant messages. The misleading "Update print statement from 'Hello' to 'Goodbye'" commit on the v1 spec is the kind of failure this prevents.

**Allowed types (V2):** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`.

**Allowed scopes (V2):** `memory`, `runtime`, `ui`, `agent`, `prompt`, `infra`, `ci`, `docs`, `migration`, `repo`, `auth`, `obs` (observability), `ops`.

Examples:
- `feat(memory): add outbox pattern for write durability` — T0.B2
- `fix(prompt): resolve helm_prompt.md brain.sh references` — T0.B6
- `docs(spec): create T1 Launch Spec V2` — this PR
- `chore(repo): add AGENTS.md operating contract` — T0.A1

---

## Progress Tracker

### Phase 0 — Foundation (sequential, must complete before Phase 2)

#### Sub-phase 0A — Repo & Operational Foundation (lands FIRST)

| Task | Description | Tier | Status |
|---|---|---|---|
| T0.A1 | Repo operating contract — AGENTS.md (vendor-neutral), Conventional Commits, ADR template, runbook template | STOP | 🔵 Queued |
| T0.A2 | Pre-commit hooks — ruff, black, eslint, prettier, commitlint | Batch | 🔵 Queued |
| T0.A3 | Test harness — pytest (Python) + vitest (JS) skeletons | STOP | 🔵 Queued |
| T0.A4 | CI pipeline — GitHub Actions: lint + typecheck + test on every PR | STOP | 🔵 Queued |
| T0.A5 | Type discipline — mypy strict for Python; helm-ui type strategy decision (ADR-001) | STOP | 🔵 Queued |
| T0.A6 | Observability foundation — structlog standard, correlation IDs, OpenTelemetry tracer (no exporter yet) | STOP | 🔵 Queued |
| T0.A7 | Deployment hardening — multi-stage Dockerfile, non-root user, HEALTHCHECK, .dockerignore, pinned base images | ARCH | 🔵 Queued |
| T0.A8 | API auth — HELM_API_TOKEN bearer middleware on /invoke and /events | ARCH | 🔵 Queued |
| T0.A9 | Migration discipline — numbered, idempotent, schema dump baseline, ADR-002 reversibility policy | STOP | 🔵 Queued |
| T0.A10 | Backup + restore runbook — pg_dump nightly, restore drill | STOP | 🔵 Queued |
| T0.A11 | Cost guardrails — embedding $/day cap, daily-spend logger, kill switch | STOP | 🔵 Queued |
| T0.A12 | CI: container build + GHCR publish on merge to main | ARCH | 🔵 Queued |
| T0.A13 | CI: secrets scanning (gitleaks) on every push | Batch | 🔵 Queued |
| T0.A14 | CI: dependency automation (Dependabot config, grouped weekly PRs) | STOP | 🔵 Queued |
| T0.A15 | CI: weekly cost summary issue from `helm.cost` log events | Batch | 🔵 Queued |

#### Sub-phase 0B — Memory Foundation (was v1's T0.1–T0.6)

| Task | Description | Tier | Status |
|---|---|---|---|
| T0.B1 | Memory module — core package, Pydantic models, client, settings | ARCH | 🔵 Queued |
| T0.B2 | Memory module — durable outbox (SQLite, not JSONL) | ARCH | 🔵 Queued |
| T0.B3 | Migrate in-process agents to memory module | ARCH | 🔵 Queued |
| T0.B4 | Snapshot service — replace snapshot.sh, atomic writes via os.replace | STOP | 🔵 Queued |
| T0.B5 | Prompt management — replace sync/pull scripts, refuse-to-boot fallback | STOP | 🔵 Queued |
| T0.B6 | Shell deprecation + complete prompt/doc rewrite (4 files) | STOP | 🔵 Queued |

### Phase 1 — Freestanding UI (can start in parallel with Phase 0; in single-dev mode, runs interleaved)

| Task | Description | Tier | Status |
|---|---|---|---|
| T1.1 | Remove Speaker from mockData.js, rename to subsystems_invoked | Batch | 🔵 Ready |
| T1.2 | Update mock IDs to UUIDs | Batch | 🔵 Ready |
| T1.3 | Hardcode personality translations in widget | Batch | 🔵 Ready |
| T1.4 | Date formatting utility | Batch | 🔵 Ready |
| T1.5a | Glass morphism — define CSS design tokens | Batch | 🔵 Ready |
| T1.5b | Glass morphism — apply tokens across components | STOP | 🔵 Ready |
| T1.6 | Commit Supabase anon key to repo (.env) | Batch | 🔵 Ready |
| T1.7 | UI Interaction Spec document (HARD GATE) | ARCH | 🔵 Ready |

> **T1.7 is a hard gate.** Phase 2 does not open until T1.7 is reviewed and accepted by Architect + Maxwell. T1.7 defines the contracts T2.3 builds against.

### Phase 2 — Backend Build (requires Phase 0 complete + T1.7 locked)

| Task | Description | Tier | Status |
|---|---|---|---|
| T2.1 | ABSORBED INTO T0.B5 | — | ✅ Replaced |
| T2.2 | Contemplator→Archivist async handoff (via memory module) | STOP | 🔵 Queued |
| T2.3 | SSE endpoint + UI directives + prompt caching | ARCH | 🔵 Queued |
| T2.4 | Add slug column to helm_beliefs | Batch | 🔵 Queued |
| T2.5 | Belief observation history (helm_belief_history) | STOP | 🔵 Queued |
| T2.6 | Signals table + dual-write hook in memory module | ARCH | 🔵 Queued |
| T2.7 | RPC function get_entities_with_counts() | Batch | 🔵 Queued |
| T2.9 | Agent simulation test harness (canned conversations, mocked LiteLLM, asserts SSE + memory writes) | ARCH | 🔵 Queued |
| T2.8 | Schema reference doc (Widget Data Map) — LAST | STOP | 🔵 Queued |

### Phase 3 — Integration + Launch Validation (⛔ blocked on Phase 2 + Phase 0 complete)

| Task | Description | Tier | Status |
|---|---|---|---|
| T3.1 | JSON + fallback response parser | Batch | 🔴 Blocked on T2.3 |
| T3.2 | executeDirective() handler | Batch | 🔴 Blocked on T2.3 |
| T3.3 | Connect UI to real Supabase (per-widget feature flags) | STOP | 🔴 Blocked on T1.6 + T2.4–T2.7 |
| T3.4 | Connect UI to real runtime (chat + SSE + node state + auth header) | STOP | 🔴 Blocked on T0.A8 + T2.3 |
| T3.5 | T1 Launch validation (the "Helm cares" test) | STOP | 🔴 Blocked on T3.1–T3.4 |

### Phase 4 — Operational Readiness (closes T1)

| Task | Description | Tier | Status |
|---|---|---|---|
| T4.1 | Runbook set — incident response, common failure modes (10+ runbooks) | STOP | 🔵 Queued |
| T4.2 | Rate limiting on /invoke endpoint (token bucket, per-token) | STOP | 🔵 Queued |
| T4.3 | SSE session resumption protocol — Last-Event-ID + replay buffer | ARCH | 🔵 Queued |
| T4.4 | Dev deployment decision (ADR-003) — Vercel + Render + Supabase project-column partitioning | STOP | 🔵 Queued |
| T4.11 | Persistent dev deployment — main → Vercel (UI) + Render (runtime), 24/7 stable URL, warmup cron | ARCH | 🔵 Queued |
| T4.6 | Preview environments per PR — Vercel native previews + Render per-PR + Supabase project partition | ARCH | 🔵 Queued |
| T4.7 | Scheduled health checks — cron-driven `/health` + canary `/invoke` | STOP | 🔵 Queued |
| T4.8 | Performance regression baseline + bench (latency on canned inputs) | STOP | 🔵 Queued |
| T4.9 | Docs site auto-deploy (GitHub Pages: V2 spec, ADRs, runbooks) | Batch | 🔵 Queued |
| T4.10 | Release automation (semantic-release, auto-changelog, GitHub releases) | STOP | 🔵 Queued |
| T4.5 | Operational SITREP — close Stage 1 T1 | STOP | 🔵 Queued |

### Previously Completed (carry-forward from v1)

| Task | Description | Status |
|---|---|---|
| RLS policies on all 8 brain tables | ✅ Done |
| Supabase Realtime on all 7 tables | ✅ Done |
| Console drawer + chat tab (PR #81) | ✅ Done |
| Activity/System tabs + split view (PR #81) | ✅ Done |
| Docked widgets + minimize pills (PR #81) | ✅ Done |
| Position settings + full-screen + slash commands | ✅ Done |
| Widget viewport clamping + quadrant stacking | ✅ Done |
| Lane C refounding (PRs #73–87) | ✅ Done |

---

## Execution Order (Single Dev)

The user-facing task IDs are grouped by phase, but in single-dev sequential mode the actual landing order is:

```
1.  T0.A1   Repo operating contract            [must be FIRST — sets the rules]
2.  T0.A2   Pre-commit hooks                   [enforce the rules]
3.  T0.A3   Test harness                       [give CI something to run]
4.  T0.A4   CI pipeline (lint + test + build)  [enforce on every PR from now]
5.  T0.A5   Type discipline + ADR-001          [decide JS vs TS for helm-ui]
6.  T0.A6   Observability foundation           [structlog convention before more code]
7.  T0.A7   Deployment hardening               [Dockerfile is touched by everything later]
8.  T0.A12  CI: container build + GHCR push    [needs T0.A7 Dockerfile shape]
9.  T0.A13  CI: secrets scanning (gitleaks)    [cheap, zero-friction add]
10. T0.A14  CI: dependency automation          [keeps pinned deps current]
11. T0.A9   Migration discipline + baseline    [before any new migration; includes CI migration safety]
12. T0.A8   API auth middleware                [before /invoke is a public surface]
13. T0.A10  Backup + restore runbook           [paranoia before we start moving data around]
14. T0.A11  Cost guardrails                    [before embedding-heavy work begins]
15. T0.A15  CI: weekly cost summary issue      [pairs with T0.A11 — visibility on top of cap]
16. T0.B1   Memory module — core               [start of memory work]
17. T0.B2   Memory module — outbox
18. T0.B3   Migrate agents
19. T0.B4   Snapshot service
20. T0.B5   Prompt management
21. T0.B6   Shell deprecation + 4-file rewrite
22. T1.1    UI: Speaker removal + subsystems_invoked rename
23. T1.2    UI: UUID mocks
24. T1.3    UI: hardcode personality translations
25. T1.4    UI: date formatting utility
26. T1.5a   UI: CSS design tokens
27. T1.5b   UI: apply tokens across components
28. T1.6    UI: commit Supabase anon key
29. T1.7    UI Interaction Spec [HARD GATE — Architect + Maxwell]
30. T2.2    Async handoff
31. T2.3    SSE + directives + caching
32. T2.9    Agent simulation test harness      [needs T2.3 SSE contract + T0.B5 prompt module]
33. T2.4    Belief slugs
34. T2.5    Belief history
35. T2.6    Signals table + dual-write hook
36. T2.7    Entities RPC
37. T2.8    Schema reference doc
38. T3.1    Response parser
39. T3.2    Directive handler
40. T3.3    UI ↔ Supabase
41. T3.4    UI ↔ runtime
42. T3.5    Launch validation
43. T4.1    Runbook set
44. T4.2    Rate limiting
45. T4.3    SSE session resumption
46. T4.4    Dev deployment decision (ADR-003)
47. T4.11   Persistent dev deployment (Vercel + Render, stable URL)  [implements ADR-003]
48. T4.6    Preview environments per PR        [reuses T4.11 stack, ephemeral instances]
49. T4.7    Scheduled health checks            [needs T4.11 deployed instance]
50. T4.8    Performance regression baseline    [needs T4.11 deployed instance to bench against]
51. T4.9    Docs site auto-deploy
52. T4.10   Release automation
53. T4.5    Operational SITREP — T1 close
```

53 tasks. Some bundle (T1.1+T1.2 batch, T2.4+T2.7 batch, T4.9+T4.10 batch) — true PR count ~49–57.

---

## Phase 0A — Repo & Operational Foundation

### T0.A1 — Repo Operating Contract

**Purpose:** Establish the rules of engagement before any code is written under V2. This is the operating contract for me, for Architect, and for any future contributor.

**Helm is model-agnostic.** The operating contract is authored in `AGENTS.md` — the emerging vendor-neutral convention picked up by Claude Code, Cursor, Aider, Codex, and other agentic coding tools. No Claude branding in the canonical file. Where a tool requires its own filename (e.g., legacy Claude Code installations expecting `CLAUDE.md`, Cursor expecting `.cursorrules`), a one-line shim file points at `AGENTS.md`. Shims are disposable as the agent landscape converges.

**Deliverables:**

1. **`AGENTS.md`** at repo root — vendor-neutral instructions to any agent working in this repo. Contents:
    - V2 spec is canonical for T1 work
    - Conventional Commits required
    - All non-trivial work goes through STOP gates
    - Test harness exists; new code includes tests
    - Structured logging convention (`structlog`, `helm.<module>` logger names, correlation IDs)
    - Memory writes go through `memory.write()` — never raw `supabase_client` or shell
    - Don't claim a PR is ready until CI passes
    - Reference to `docs/runbooks/` for known failure modes
2. **Optional vendor shims** at repo root if a tool in active use doesn't auto-discover `AGENTS.md`. Each is one line: `See AGENTS.md`. None added speculatively — only when a real tool needs one. Initial set: empty (Claude Code is the only agent in active use, and it reads `AGENTS.md` natively).
3. **`docs/adr/` directory** with ADR template (`docs/adr/0000-template.md`) following the [Michael Nygard ADR format](https://github.com/joelparkerhenderson/architecture-decision-record/tree/main/locales/en/templates/decision-record-template-by-michael-nygard).
4. **`docs/runbooks/` directory** with runbook template (`docs/runbooks/0000-template.md`) — symptom, diagnosis, fix, root cause links.
5. **`commitlint.config.js`** at repo root with the allowed types and scopes from the V2 spec.
6. **`CONTRIBUTING.md`** — short, points to `AGENTS.md`, V2 spec, and the ADR + runbook directories. Solo project, but the discipline is for future-me as much as a contributor.

**Out of scope (deferred to T0.A2):** Pre-commit hook installation. T0.A1 only adds the configs; T0.A2 wires them into git.

**STOP gate.** Maxwell reviews the operating contract before anything else lands.

---

### T0.A2 — Pre-commit Hooks

**Purpose:** Enforce the rules locally before they hit CI. Cheap, fast, in-loop feedback.

**Tooling:** [pre-commit framework](https://pre-commit.com/) — language-agnostic hook runner, widely adopted, single config file.

**`.pre-commit-config.yaml`:**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: commitlint
        name: commitlint
        entry: npx --no-install commitlint --edit
        language: system
        stages: [commit-msg]

      - id: eslint
        name: eslint
        entry: cd helm-ui && npm run lint
        language: system
        files: ^helm-ui/.*\.(js|jsx|ts|tsx)$
        pass_filenames: false
```

**Setup steps documented in `AGENTS.md`:**

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
cd helm-ui && npm install --save-dev @commitlint/cli @commitlint/config-conventional eslint
```

**Batch tier.** Mechanical config addition.

---

### T0.A3 — Test Harness

**Purpose:** Give CI something to run. Not full coverage — just the harness, conventions, and one passing test per language.

**Python (`services/helm-runtime/`):**
- Add `pytest`, `pytest-asyncio`, `pytest-cov` to `requirements-dev.txt`
- Add `pyproject.toml` `[tool.pytest.ini_options]` block — set `asyncio_mode = "auto"`, set `testpaths = ["tests"]`
- Create `services/helm-runtime/tests/` with `__init__.py`, `conftest.py` (Supabase fixture stub), and `test_smoke.py` (one passing test that imports `main`)

**JavaScript (`helm-ui/`):**
- Add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` to devDependencies
- Add `vitest.config.js` with `environment: 'jsdom'`
- Create `helm-ui/src/__tests__/smoke.test.jsx` with one passing test
- Add `npm test` script

**Conventions documented in `AGENTS.md`:**
- Python tests live next to subjects (memory module → `tests/test_memory_writer.py`)
- JS tests use `*.test.jsx` co-located with components
- New code must include tests (PR template enforces)
- One assertion per test where practical

**Coverage targets (V2):**
- T0.B1–T0.B6 memory module → 80%+ unit coverage (this is the foundation; it has to be solid)
- T2.x runtime additions → 60%+ coverage
- T3.x UI integration → smoke + critical-path tests, not full coverage
- Phase 4 → no coverage requirement, runbooks substitute

**STOP gate.** Sets the testing convention for the rest of V2.

---

### T0.A4 — CI Pipeline

**Purpose:** Enforce the operating contract on every PR.

**Stack:** GitHub Actions — already wired via repo, no new infrastructure.

**`.github/workflows/ci.yml`:** Three parallel jobs.

```yaml
name: CI
on: [pull_request, push]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Install
        run: |
          cd services/helm-runtime
          pip install -r requirements.txt -r requirements-dev.txt
      - name: Lint
        run: cd services/helm-runtime && ruff check . && ruff format --check .
      - name: Type check
        run: cd services/helm-runtime && mypy . --strict
      - name: Test
        run: cd services/helm-runtime && pytest --cov --cov-report=term

  ui:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Install
        run: cd helm-ui && npm ci
      - name: Lint
        run: cd helm-ui && npm run lint
      - name: Test
        run: cd helm-ui && npm test -- --run
      - name: Build
        run: cd helm-ui && npm run build

  commitlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install --save-dev @commitlint/cli @commitlint/config-conventional
      - run: npx commitlint --from origin/main --to HEAD
```

**Branch protection on `main`:** All three jobs must pass before merge. Maxwell sets this in GitHub settings as part of T0.A4 post-merge.

**STOP gate.** Architect-tier impact (changes the merge workflow).

---

### T0.A5 — Type Discipline (ADR-001)

**Purpose:** Static guarantees over runtime surprises.

**Python:** `mypy --strict` on `services/helm-runtime/`. All function signatures typed. Pydantic models cover boundary validation. Type stubs for httpx, structlog where needed.

**JavaScript:** ADR-001 decides between two paths:

- **Path A (TypeScript conversion):** Convert `helm-ui` from JSX to TSX. ~3 PRs of mechanical work, durable type safety, better tooling integration. Cost: noisy diff, requires every component to be touched.
- **Path B (JSDoc + ESLint strict):** Keep JSX. Add JSDoc type comments on exported functions and component props. ESLint with `eslint-plugin-jsdoc` enforces. Cheaper, less noisy, but lighter guarantees.

**My recommendation:** Path A. The frontend is small (~30 files) and growing. T1.5b touches every component anyway — bundle the TS conversion with the design-token application. Two birds.

**ADR-001** documents the decision, the rejected path, and the rationale. Maxwell signs the ADR.

**STOP gate.** ADR-001 is the artifact; the decision sets the trajectory for Phase 1.

---

### T0.A6 — Observability Foundation

**Purpose:** Structured logging convention + correlation IDs everywhere + tracing primitives. No exporter yet — that's a deployment concern. The convention must be in place before T0.B1 lands so the memory module is born observable.

**`services/helm-runtime/observability.py`:**

```python
import structlog
import logging
from contextvars import ContextVar
from uuid import uuid4

# Correlation ID context var — set per request, propagates to all logs in that request
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid4())
        correlation_id_var.set(cid)
    return cid

def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging — call once at startup."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger. Use 'helm.<module>' naming convention."""
    return structlog.get_logger(name)
```

**FastAPI middleware** (added in `main.py`):

```python
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("x-correlation-id", str(uuid4()))
    correlation_id_var.set(cid)
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()
    response.headers["x-correlation-id"] = cid
    return response
```

**OpenTelemetry tracer (no exporter):**

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("helm.runtime")

# Spans wrap memory writes, agent invocations, Supabase calls
async def write(self, ...):
    with tracer.start_as_current_span("memory.write") as span:
        span.set_attribute("project", project)
        span.set_attribute("agent", agent)
        ...
```

No exporter (no Jaeger, no OTLP collector) lands in T1. Spans are just structured. T4 / Stage 2 wires an exporter when there's a place to send them.

**Logging convention (committed in `AGENTS.md`):**
- Logger name: `helm.<module>` — `helm.memory`, `helm.runtime`, `helm.agent.contemplator`
- Event names: `dotted.snake_case` — `memory.write`, `memory.write.failed`, `agent.invoked`
- Every event includes `correlation_id` (auto-bound)
- Every error event includes `error` field (str), `error_type` field (cls name), and traceback
- `info` for normal events, `warning` for recoverable issues, `error` for failures, `critical` for things that should page

**Dependencies added:** `structlog>=24.0.0`, `opentelemetry-api>=1.25.0`, `opentelemetry-sdk>=1.25.0`

**STOP gate.** Sets the logging shape for everything after.

---

### T0.A7 — Deployment Hardening (ARCH)

**Purpose:** Dockerfile and docker-compose stack become production-shaped. Not yet production-deployed (deployment target is ADR-003 in T4.4) but production-shaped.

**Multi-stage `services/helm-runtime/Dockerfile`:**

```dockerfile
# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12.4

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
LABEL org.opencontainers.image.source="https://github.com/mconn0330-svg/hammerfall-solutions"
LABEL org.opencontainers.image.description="Helm Runtime Service"

# Non-root user
RUN groupadd -r helm && useradd -r -g helm -d /app -s /bin/bash helm

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
COPY --chown=helm:helm . .

USER helm
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`.dockerignore`** at `services/helm-runtime/.dockerignore`:

```
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
htmlcov
tests
```

**`requirements.txt` discipline:** All deps pinned to exact versions. Hash-locked via `pip-compile` (add `pip-tools` to dev deps). Renovate or Dependabot handles upgrades.

**`docker-compose.yml` updates:**
- `restart: unless-stopped` on the runtime service
- Read-only root filesystem (`read_only: true`) with `tmpfs` mounts for `/tmp`
- `cap_drop: [ALL]`
- Resource limits (`mem_limit`, `cpus`)
- Healthcheck reflected in compose
- Env from `.env` file, no inline secrets

**ARCH gate.** Architect reviews; this changes how the runtime boots.

---

### T0.A8 — API Auth (ARCH)

**Purpose:** `/invoke/*`, `/events`, `/config/*` are not anonymous endpoints. Even on localhost, a static bearer token is the minimum bar.

**Implementation:**

```python
# auth.py
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

bearer_scheme = HTTPBearer(auto_error=False)

def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    expected = os.environ.get("HELM_API_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HELM_API_TOKEN not configured",
        )
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing bearer token",
        )
    return credentials.credentials
```

**Apply to endpoints:**

```python
@app.post("/invoke/{agent_role}", dependencies=[Depends(require_token)])
async def invoke_agent(...): ...

@app.get("/events", dependencies=[Depends(require_token)])
async def events(...): ...
```

**Exempt:** `/health` (no auth — used by Docker healthcheck and external monitors).

**Token generation:** Documented in `docs/runbooks/0001-api-token-rotation.md` — `openssl rand -hex 32`, set in `.env` as `HELM_API_TOKEN=...`, restart runtime.

**Frontend integration deferred to T3.4** — `helm-ui/.env` gains `VITE_HELM_API_TOKEN` (NOT the same as Supabase anon key, separate concern). Fetch wrapper adds `Authorization: Bearer ${token}` header. The token is in client-side env, so it's not a secret in the cryptographic sense — it's a coarse auth boundary that excludes random pings. T2/Stage 2 layer real user auth on top.

**ARCH gate.** Changes the public surface contract.

---

### T0.A9 — Migration Discipline + Schema Baseline

**Purpose:** Make migrations a first-class artifact with rules, not ad-hoc SQL.

**Establish in `supabase/migrations/`:**
- Numbered: `YYYYMMDDHHMMSS_description.sql`
- Idempotent where feasible: `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`
- Reversibility documented in a comment block at top of each migration. `DOWN:` section even if not auto-applied — at least it's documented.
- One logical change per migration

**Schema baseline:** Commit `supabase/schema_baseline.sql` — full `pg_dump --schema-only` of the current Supabase project state. Future migrations are deltas from this baseline. Rebuild from scratch = baseline + all migrations.

**ADR-002:** "Migration Reversibility Policy" — documents which categories of change need a rollback migration vs. a documented manual revert. Drops, renames, type changes always need rollback. Index adds, RLS policy adds don't.

**`scripts/migrate.sh`** (legitimate shell — operator tool, not memory write path):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Usage: ./scripts/migrate.sh [push|verify|baseline-dump]
cd "$(dirname "$0")/.."
case "${1:-push}" in
  push) supabase db push ;;
  verify) supabase db diff --schema public ;;
  baseline-dump) pg_dump "$SUPABASE_DB_URL" --schema-only --schema=public > supabase/schema_baseline.sql ;;
  *) echo "usage: $0 [push|verify|baseline-dump]"; exit 1 ;;
esac
```

**CI migration safety (`.github/workflows/migration-check.yml`):**

```yaml
name: Migration Safety
on:
  pull_request:
    paths: ['supabase/migrations/**']
jobs:
  apply-and-verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: supabase/setup-cli@v1
      - name: Create ephemeral Supabase branch
        run: supabase branches create ci-pr-${{ github.event.pull_request.number }}
        env: { SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }} }
      - name: Apply all migrations to branch
        run: supabase db push --linked --branch ci-pr-${{ github.event.pull_request.number }}
      - name: Schema diff vs baseline (sanity check)
        run: supabase db diff --linked --branch ci-pr-${{ github.event.pull_request.number }} > diff.sql
      - name: Verify reversibility (DOWN comment present for destructive ops)
        run: ./scripts/check_migration_reversibility.py supabase/migrations/
      - name: Cleanup ephemeral branch
        if: always()
        run: supabase branches delete ci-pr-${{ github.event.pull_request.number }} --force
```

The reversibility check parses the `DOWN:` comment block required by ADR-002 — fails if a migration that drops/renames/retypes is missing one.

**STOP gate.**

---

### T0.A10 — Backup + Restore Runbook

**Purpose:** A documented, tested path back from "I broke the brain."

**`docs/runbooks/0002-supabase-backup-restore.md`:**

1. **Backup procedure** — `pg_dump $SUPABASE_DB_URL > backups/helm-brain-$(date +%Y%m%d).sql`. Daily via cron (manual cron entry, since no production server yet — local cron acceptable). Backups land in `~/helm-backups/` (NOT in repo — too large). Keep 30 days, manually rotate.
2. **Restore procedure** — staging-first. Spin up a Supabase branch (or local Postgres), `psql < backup.sql`, verify counts, then promote. Never restore directly to prod.
3. **Restore drill** — at T0.A10 close, do one full restore drill against a test Supabase project. Document any friction in the runbook.
4. **What's NOT backed up** — RLS policies (re-applied by re-running migrations), Auth users (no users yet), Storage buckets (none).

**Backup automation in T1:** Manual + documented. T4.1 / Stage 2 considers automation.

**STOP gate.** Maxwell confirms the restore drill works.

---

### T0.A11 — Cost Guardrails

**Purpose:** Prevent silent cost overruns. T1 doesn't have many embedding calls yet, but T2.6 (signals) and Contemplator passes will increase volume. Establish the cap and the meter before the volume rises.

**Implementation:**

```python
# cost_guard.py
import asyncio
from datetime import date
from collections import defaultdict
from observability import get_logger

logger = get_logger("helm.cost")

class CostGuard:
    """Tracks daily embedding spend; raises if cap exceeded."""
    
    EMBEDDING_COST_PER_1K_TOKENS = 0.00013  # OpenAI text-embedding-3-small
    
    def __init__(self, daily_cap_usd: float = 5.0):
        self.daily_cap_usd = daily_cap_usd
        self._spend_by_day: dict[date, float] = defaultdict(float)
        self._lock = asyncio.Lock()
    
    async def check_and_record(self, tokens: int, model: str = "embedding") -> None:
        cost = (tokens / 1000) * self.EMBEDDING_COST_PER_1K_TOKENS
        today = date.today()
        async with self._lock:
            if self._spend_by_day[today] + cost > self.daily_cap_usd:
                logger.critical(
                    "cost.cap_exceeded",
                    spent_today=self._spend_by_day[today],
                    cap=self.daily_cap_usd,
                    blocked_call_cost=cost,
                )
                raise CostCapExceeded(
                    f"Daily embedding cap ${self.daily_cap_usd} would be exceeded"
                )
            self._spend_by_day[today] += cost
            logger.info(
                "cost.recorded",
                model=model,
                tokens=tokens,
                cost=cost,
                day_total=self._spend_by_day[today],
            )

class CostCapExceeded(Exception): ...
```

**Initial cap:** `$5.00/day` for embeddings. Configurable via `HELM_COST_DAILY_CAP_USD`. Maxwell can raise/lower based on observed usage.

**Anthropic call cost** is harder to meter precisely (input + output tokens, prompt caching discounts) — V2 logs every Anthropic call's `usage` block but does not impose a per-day cap on Anthropic in T1. ADR-noted, deferred.

**Integration:** Embedding client (`embedding_client.py`) calls `cost_guard.check_and_record()` before every embedding. On `CostCapExceeded`, the call is rejected, the requesting agent gets an error with a clear message, and the runtime continues.

**STOP gate.**

---

### T0.A12 — CI: Container Build + GHCR Publish (ARCH)

**Purpose:** Every merge to `main` builds a Docker image and pushes it to GitHub Container Registry. Eliminates "works on my machine" — deployment becomes "pull a known-good image." Required substrate for T4.6 (preview environments) and T4.7 (deployed health checks).

**`.github/workflows/build-publish.yml`:**

```yaml
name: Build & Publish
on:
  push:
    branches: [main]
    paths:
      - 'services/helm-runtime/**'
      - '.github/workflows/build-publish.yml'
  pull_request:
    paths:
      - 'services/helm-runtime/**'

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        if: github.event_name == 'push'
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}/helm-runtime
          tags: |
            type=ref,event=branch
            type=sha,prefix=,format=short
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: services/helm-runtime
          push: ${{ github.event_name == 'push' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Behavior:**
- PRs build but don't push (catches Dockerfile breakage before merge)
- Merges to `main` build + push tagged with `latest`, branch name, and short SHA
- BuildKit cache via GitHub Actions cache backend — second-run builds in seconds

**Image visibility:** Public on GHCR by default. Maxwell flips to private in repo settings if Helm code becomes sensitive (no per-PR action needed; setting persists).

**Vulnerability scanning:** Add `aquasecurity/trivy-action` step on the merged image. Failures don't block merge (Helm doesn't have a security team), but the report is a PR comment for visibility.

**ARCH gate.** Adds GHCR as a deployment dependency.

---

### T0.A13 — CI: Secrets Scanning (Batch)

**Purpose:** Block accidental key commits. Service keys, API tokens, OAuth secrets — gitleaks catches the obvious patterns before they hit the public history.

**`.github/workflows/gitleaks.yml`:**

```yaml
name: Secrets Scan
on: [pull_request, push]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**`.gitleaks.toml`:** Allowlist for the Supabase anon key (committed by design per T1.6) and any other intentional public values. Comment each entry with the rationale.

**Pre-commit mirror:** Add gitleaks to `.pre-commit-config.yaml` (T0.A2 amended) so devs catch leaks locally before push.

**Batch tier.** Mechanical addition.

---

### T0.A14 — CI: Dependency Automation

**Purpose:** Pinned dependencies (per T0.A7) stay current without manual tracking. Renovate or Dependabot opens grouped weekly PRs; CI validates them; Maxwell merges or skips.

**Choice — Dependabot.** Native to GitHub, zero-cost, no third-party app install. Renovate is more powerful (better grouping, broader ecosystem support) but requires app install and config tuning. T1 picks Dependabot for simplicity; Stage 2 can flip to Renovate if needed.

**`.github/dependabot.yml`:**

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: /services/helm-runtime
    schedule: { interval: weekly, day: monday }
    groups:
      production:
        patterns: ['*']
        exclude-patterns: ['pytest*', 'mypy*', 'ruff*', 'pre-commit*']
      development:
        patterns: ['pytest*', 'mypy*', 'ruff*', 'pre-commit*']
    open-pull-requests-limit: 5

  - package-ecosystem: npm
    directory: /helm-ui
    schedule: { interval: weekly, day: monday }
    groups:
      production:
        dependency-type: production
      development:
        dependency-type: development
    open-pull-requests-limit: 5

  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: weekly, day: monday }

  - package-ecosystem: docker
    directory: /services/helm-runtime
    schedule: { interval: weekly, day: monday }
```

**Auto-merge for patch/minor on dev deps:** Optional GitHub Actions workflow that auto-approves + merges Dependabot PRs that pass CI and only update dev dependencies. T0.A14 ships the config but auto-merge is opt-in (Maxwell decides at PR time).

**STOP gate.**

---

### T0.A15 — CI: Weekly Cost Summary

**Purpose:** T0.A11 caps spend. T0.A15 tells Maxwell what was actually spent. Pairs the guardrail with visibility.

**Source of truth:** `helm.cost` structured log events emitted by `cost_guard` (T0.A11). The runtime ships logs to a queryable destination — for T1, that's container `stdout` captured by Docker logging driver. The CI job pulls last 7 days of log files (or queries log aggregator if Stage 2 wires one) and computes a summary.

**`.github/workflows/cost-summary.yml`:**

```yaml
name: Weekly Cost Summary
on:
  schedule:
    - cron: '0 14 * * MON'   # Monday 14:00 UTC
  workflow_dispatch:

jobs:
  summarize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Pull last 7d cost events
        run: |
          # Fetch from log destination (S3, Loki, container logs API, etc.)
          # T1 implementation: fetches from a configured endpoint
          ./scripts/fetch_cost_events.py --days 7 > cost_events.json
      - name: Summarize
        run: ./scripts/cost_summary.py cost_events.json > summary.md
      - name: Open issue
        uses: peter-evans/create-issue-from-file@v5
        with:
          title: "Weekly cost summary — week of ${{ github.event.schedule }}"
          content-filepath: summary.md
          labels: cost,automation
```

**`scripts/cost_summary.py`** computes: total spend, breakdown by model, top 5 spike days, week-over-week delta, projection of monthly spend at current rate. Markdown output is the issue body.

**Note on log retrieval:** At T1, the runtime runs in one container on one host; logs are local. The fetch script may need a passwordless SSH key or a small read-only HTTP endpoint on the host. T0.A15 PR description picks the mechanism.

**Batch tier.**

---

## Phase 0B — Memory Foundation

Same scope as v1 T0.1–T0.6, with the gap-analysis fixes layered in.

---

### T0.B1 — Memory Module Core (ARCH)

**What:** v1 T0.1, with the following V2 fixes applied:

#### Fix 1 — Expand `MemoryType` enum

v1 enum is too narrow. The runtime writes more types than v1 listed.

```python
class MemoryType(str, Enum):
    # Cognitive frame writes (Projectionist)
    FRAME = "frame"
    # Long-form memory (Archivist)
    BEHAVIORAL = "behavioral"
    DECISION = "decision"
    CORRECTION = "correction"
    # Pattern detection (Contemplator) — triggers signals dual-write
    PATTERN = "pattern"
    # Observation (Contemplator)
    OBSERVATION = "observation"
    # Inner monologue (Contemplator)
    MONOLOGUE = "monologue"
    # Belief lifecycle (Contemplator)
    BELIEF_UPDATE = "belief_update"
    # Entity / relationship (Archivist)
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    # Generic scratchpad (any agent, transient)
    SCRATCHPAD = "scratchpad"
```

#### Fix 2 — Pydantic Settings uses `env_file` and `env_prefix`

```python
class MemorySettings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    retry_attempts: int = 3
    retry_backoff_base: float = 1.0
    retry_backoff_max: float = 30.0
    timeout_seconds: float = 10.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown: float = 30.0
    outbox_path: Path = Path.home() / ".helm" / "outbox.db"
    
    model_config = SettingsConfigDict(
        env_prefix="HELM_MEMORY_",
        env_file=".env",
        extra="ignore",
    )
```

OS-aware default for `outbox_path` — `Path.home() / ".helm" / "outbox.db"` works on macOS, Linux, and Windows. v1's `/tmp/helm-outbox.jsonl` was Linux-only.

#### Fix 3 — Datetime UTC aware everywhere

```python
from datetime import datetime, timezone
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

Replace every `datetime.utcnow()` (deprecated in Python 3.12+, returns naive datetime). Centralize in `memory/_time.py`.

#### Fix 4 — Circuit breaker emits observability events

```python
class CircuitBreaker:
    def open(self):
        self._state = "open"
        self._opened_at = utc_now()
        logger.warning(
            "circuit_breaker.opened",
            consecutive_failures=self._failure_count,
            cooldown_seconds=self.cooldown,
        )
        # Hook for SSE — emit event so System tab surfaces it
        self._on_state_change("open")
    
    def close(self):
        self._state = "closed"
        logger.info("circuit_breaker.closed")
        self._on_state_change("closed")
```

The `_on_state_change` callback is wired in T2.3 to the SSE event bus. v1 had the breaker logic but no observability.

#### Fix 5 — Tracing spans on writes

Every write opens an OpenTelemetry span (T0.A6). Span attributes include `project`, `agent`, `memory_type`, `entry_id`. Failures record exception on span.

#### Tests required

- `tests/test_models.py` — Pydantic model validation, enum membership, slug utility
- `tests/test_settings.py` — env loading, defaults, validation
- `tests/test_client.py` — retry behavior (mock httpx), circuit breaker state machine, timeout handling
- `tests/test_writer.py` — write path, failure path, observability event emission

**ARCH gate.** Architect reviews the module shape before T0.B2 builds on it.

---

### T0.B2 — Outbox Pattern (ARCH)

**Storage choice — SQLite, not JSONL.**

v1 specified JSONL. JSONL has a concurrency race: two processes appending simultaneously corrupt entries (POSIX `O_APPEND` is atomic per `write()` but not across multiple writes). Drain-then-truncate has a window where new appends are lost.

SQLite gives:
- ACID transactions on enqueue and drain
- Single-file portability (no Postgres dependency, just an embedded DB)
- Built-in `aiosqlite` async driver
- Survives crashes (WAL mode)
- Cross-platform (Windows-safe)

**Schema:**

```sql
CREATE TABLE outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    payload TEXT NOT NULL,             -- JSON-serialized
    queued_at TEXT NOT NULL,           -- ISO-8601 UTC
    attempt_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_attempt_at TEXT
);

CREATE INDEX idx_outbox_queued_at ON outbox(queued_at);
```

**API:**

```python
# memory/outbox.py
class Outbox:
    def __init__(self, path: Path): ...
    
    async def enqueue(self, table: str, payload: dict) -> int:
        """Append to outbox. Returns row id."""
    
    async def drain(self, client: SupabaseClient, batch_size: int = 50) -> DrainResult:
        """Drain up to batch_size entries. Failures stay queued with attempt_count++."""
    
    async def drain_loop(self, client: SupabaseClient, interval: float = 5.0):
        """Background worker."""
    
    async def stats(self) -> OutboxStats:
        """For /health and observability."""
```

**Drain failure handling:**
- After 5 attempts, the entry is moved to `outbox_dead_letter` (separate table, manual review)
- Critical log + SSE event on dead-lettering

**Health integration:** `/health` exposes `outbox.queued_count` and `outbox.dead_letter_count`. Non-zero dead letter is a degraded health.

**Tests:**
- `tests/test_outbox.py` — enqueue, drain, retry, dead-letter, concurrent enqueue (asyncio.gather of 100 enqueues, all distinct)

**ARCH gate.**

---

### T0.B3 — Migrate In-Process Agents (ARCH)

**What:** Same scope as v1 T0.3, with explicit handling of the read path divergence.

#### V2 fix: also migrate read paths progressively

v1 said "writes are the priority, reads continue through `supabase_client` for now." V2 keeps that as the T0.B3 scope, but adds a **read-path migration plan as part of the PR description**:

| Read | T0.B3 disposition | Migrated in |
|---|---|---|
| `supabase_client.get('helm_personality')` (Prime) | Stays in `supabase_client` | Stage 2 |
| `supabase_client.get('helm_prompt')` (Prime boot) | **Moves to `memory.prompt.PromptManager.load()`** | T0.B5 |
| `supabase_client.match_memories()` (Prime context) | Stays in `supabase_client`, but renamed `read_client` | T0.B6 cosmetic |
| `supabase_client.match_beliefs()` | Stays in `supabase_client` (read-only RPC) | Stage 2 |
| Frame read by Archivist | **Moves to `memory.read_frames()`** | T0.B3 |

The principle: **writes must be unified now**; reads can stay split as long as the file is renamed `read_client.py` to make the intent clear. T0.B6 includes that rename.

#### Verification

- Run runtime, invoke a session, check structured logs for `memory.write` events from each agent
- Verify no `supabase_client.insert` or `supabase_client.post` calls remain in agent code (`grep -r "supabase_client.insert\|supabase_client.post" agents/`)
- Tests: each agent gets a `tests/agents/test_<agent>.py` smoke test that mocks the memory module and asserts the agent calls `memory.write` with expected args

**ARCH gate.**

---

### T0.B4 — Snapshot Service

**What:** Same as v1 T0.4, with these fixes:

- Use `os.replace()` not `Path.rename()` — `os.replace()` is atomic + cross-device + overwrite-safe on both POSIX and Windows. `Path.rename()` raises on Windows if target exists.
- Snapshots emit `snapshot.generated` structured log + SSE event
- Tests: mock the Supabase client, assert all 4 .md files written with expected structure

**STOP gate.**

---

### T0.B5 — Prompt Management

**What:** Same as v1 T0.5, plus:

- Container fail-mode (refuse to boot if Supabase + file both unreachable) — already in v1, V2 adds explicit test (mock both failure modes, assert RuntimeError)
- helm_prompt.md gains the SNAPSHOT header — V2 adds the exact header text to be inserted in T0.B6 (the prompt rewrite already touches this file, bundle the header insertion there)
- Migration SQL goes through T0.A9 discipline (numbered, baseline-aware)
- Tests for `PromptManager.push`, `pull`, `load` — all paths

**STOP gate.**

---

### T0.B6 — Shell Deprecation + Complete Prompt/Doc Rewrite

**Critical V2 expansion.** v1 listed only `helm_prompt.md` as needing a brain.sh sweep. Reality across the repo:

| File | brain.sh references | Status |
|---|---|---|
| `agents/helm/helm_prompt.md` | 30+ | Must rewrite Routine 4 + entity/alias/correction/curious/reasoning/pattern/people/heartbeat blocks |
| `agents/helm/archivist/archivist.md` | 7 (lines 25, 62, 125, 128, 133, 137, 141) | Must rewrite all write blocks |
| `agents/helm/contemplator/contemplator.md` | 1 explicit + meta-reference | Already says "never calls brain.sh"; just needs alignment with new memory API names |
| `management/COMPANY_BEHAVIOR.md` | 4 (lines 37, 61, 63, 82) | Must rewrite |
| `services/helm-runtime/supabase_client.py` (docstring lines 7-11) | Architectural canon of the divergence | Must rewrite docstring + rename to `read_client.py` per T0.B3 |

**Rewrite pattern — every brain.sh invocation becomes a memory.write call:**

```markdown
# Before (in agent prompt markdown)
bash scripts/brain.sh hammerfall-solutions helm pattern "Pattern — slug | statement"

# After (in agent prompt markdown — Python pseudocode the agent shows)
memory.write(
    project="hammerfall-solutions",
    agent="helm",
    memory_type="pattern",
    content="Pattern — slug | statement",
)
```

For Claude Code sessions (external agents) the prompt provides the CLI:

```bash
python -m memory.write hammerfall-solutions helm pattern "Pattern — slug | statement"
```

**Em-dash convention:** v1 detection of patterns by `content.startswith("Pattern —")` uses U+2014 EM DASH. Risk: someone types `--` and the dual-write hook misses it. V2 fix: the memory module normalizes any `Pattern --`, `Pattern -`, `Pattern—` to canonical `Pattern —` at write time, and the dual-write detection runs on normalized content. Document in T0.B6's PR.

**Scripts deleted in T0.B6:**
- `scripts/brain.sh` (replaced by `python -m memory.write` CLI)
- `scripts/snapshot.sh` (replaced by `memory.snapshot` service)
- `scripts/sync_prompt.sh` (replaced by `python -m memory.prompt push`)
- `scripts/pull_prompt.sh` (replaced by `python -m memory.prompt pull`)

**Scripts that remain (legitimately shell):**
- `scripts/pull_models.sh` — Ollama model pre-pulls
- `scripts/migrate.sh` — Supabase migration operator tool (T0.A9)

**Tests:** Smoke test for the CLI (`python -m memory.write` works end-to-end against a mock Supabase fixture).

**STOP gate.** Architect reviews the rewritten prompts.

---

## Phase 1 — Freestanding UI Tasks

These tasks have zero backend dependency. In single-dev sequential mode, they land after Phase 0 closes.

The v1 Phase 1 task content stands. V2 adds:

- T1.5b conversion to TypeScript (per ADR-001 if Path A chosen)
- T1.7 spec includes auth header from T0.A8 in the request schema (frontend will need to send `Authorization: Bearer ${VITE_HELM_API_TOKEN}`)
- All UI tasks land with vitest tests for any new components/utilities

Detailed scope for T1.1–T1.7 carried forward from v1, see [Helm_T1_Launch_Spec.md](Helm_T1_Launch_Spec.md) §Phase 1 — same content, V2 doesn't repeat verbatim. Differences:

### T1.1 — V2 Note

Rename `routing` → `subsystems_invoked` in mocks. Add a vitest test that asserts every entry in `LOGS` and `ACTIVITY` has `subsystems_invoked` as an array, never a string.

### T1.4 — V2 Note

`formatDate.js` gets a vitest test covering all four formats (`date`, `time`, `datetime`, `relative`) including edge cases (just-now, 1m ago, 1h ago, yesterday, last week, far past).

### T1.5b — V2 Note

If ADR-001 Path A: this task does TS conversion + token application in one PR. The TS conversion is the larger surface; bundle reduces churn.

### T1.6 — V2 Note

`helm-ui/.env` also gains `VITE_HELM_API_TOKEN=<token>`. Document in PR that this is a coarse boundary token, not a user-auth token.

### T1.7 — V2 Note

Spec is updated to include:
- Auth header on all `/invoke/*` and `/events` requests
- Correlation ID header convention (`x-correlation-id` — server echoes back; UI propagates per session)
- Rate-limit response shape (T4.2 formalizes; T1.7 just notes 429 + `Retry-After` will exist)
- SSE reconnection strategy (T4.3 formalizes; T1.7 documents `Last-Event-ID` will be supported)

**Architect + Maxwell hard gate.** Phase 2 does not open until T1.7 is signed.

---

## Phase 2 — Backend Build

Requires Phase 0 complete + T1.7 locked. All write operations now go through the memory module from T0.B.

The v1 Phase 2 task content stands. V2 fixes layered in:

### T2.2 — V2 Notes

- Async drain failures emit both structured logs AND `archivist_drain_failed` SSE event with `severity: "error"`, `correlation_id` (from the parent request), and `outbox_queued_count`
- Outbox pattern (T0.B2) handles the durability — Contemplator's "fire and forget" returns immediately, writes land in outbox, drain worker pushes to Supabase

### T2.3 — V2 Notes — Critical Expansion

**Part A (SSE):** all spec stands; `emit_event` is moved into `memory/events.py` so it's testable in isolation. Event schema gains `correlation_id` field.

**Part B (response format):** stands; add tests for the parser that cover JSON, plain text, JSON-without-text, and malformed JSON.

**Part C (directives):** stands.

**Part D (prompt caching):** stands. Add a comment in `helm_prime.py` next to the `cache_control` block explaining that LiteLLM's Anthropic provider passes through `cache_control` as of LiteLLM v1.x — verify exact version at implementation time and pin in `requirements.txt`.

**V2 addition — circuit breaker hooks:**
The circuit breaker callback from T0.B1 wires here. When `circuit_breaker.opened` fires, emit an SSE `system_health` event with `status: "degraded"`, `details: {component: "supabase", state: "circuit_open"}`. When closed, emit `status: "healthy"`.

**V2 addition — emit point ownership:**
Move ALL `emit_event` calls into a small set of well-defined hook points instead of scattering 12+ calls through `main.py`. Specifically:
- `emit_agent_invoked` decorator on `/invoke/*` handlers
- `memory.write` emits `frame_written`, `belief_updated`, etc. via post-write hooks
- Health check emits `system_health` on every check
- This gives the UI a stable contract and makes adding events later a one-line change

**Deliverable:** Split into 2 PRs as v1 specified.

### T2.4–T2.7 — V2 Notes

Carried forward from v1 with T0 fixes already noted (slug utility lives in `memory/models.py`, dual-write hook is in `memory/writer.py`, transactional safety addressed below).

**V2 addition for T2.6 — Dual-write transaction safety:**

The hook does two writes: `helm_signals` (upsert) and `helm_memory` (insert). What happens if the first succeeds and the second fails?

V2 design:
1. **Order matters**: write `helm_memory` first (the canonical event), then `helm_signals` (the derived view).
2. **If `helm_memory` fails**: the whole `memory.write()` raises. No signal write happens. Caller sees the error.
3. **If `helm_memory` succeeds but `helm_signals` fails**: log a `signal_dual_write_failed` warning, enqueue the signal write to the outbox with `table: "helm_signals"`, return the entry id from `helm_memory`. Outbox drain will retry. Eventual consistency.
4. **No two-phase commit**: that's overkill for an audit-trail mirror table. The signal table is reconstructable from `helm_memory` if it ever drifts (separate reconciliation job in Stage 2).

Document this in the T2.6 PR description.

### T2.9 — Agent Simulation Test Harness (ARCH)

**Purpose:** Helm's behavior IS the product. A prompt edit, a Routine 4 change, a directive parser tweak — any of these can break behavior in ways unit tests don't see. T2.9 is the regression net for behavior.

**Approach:** pytest-driven canned conversations. The harness:

1. Mocks LiteLLM (`responses` library or `pytest-httpx`) so no Anthropic / Ollama calls happen — deterministic, free, fast
2. Loads a canned conversation script from `services/helm-runtime/tests/simulations/<scenario>.yaml`
3. Drives the runtime through the script (`/invoke` per turn)
4. Captures emitted SSE events, memory writes (against in-memory Supabase mock), structured logs
5. Asserts the captured trace matches the scenario's `expected:` block

**Scenario file shape:**

```yaml
# tests/simulations/01_basic_pattern_capture.yaml
name: basic pattern capture triggers signal dual-write
turns:
  - user: "I keep over-engineering when I'm excited about a project."
    mocked_anthropic_response: |
      {
        "text": "Heard. I'll watch for that.",
        "subsystems_invoked": ["contemplator"],
        "ui_directives": []
      }
    expected:
      sse_events:
        - {type: agent_invoked, agent: helm_prime}
        - {type: contemplator_pass_started}
        - {type: contemplator_pass_completed}
        - {type: agent_completed, agent: helm_prime}
      memory_writes:
        - {agent: contemplator, memory_type: pattern, content_contains: "over-engineer"}
        - {table: helm_signals, content_contains: "over-engineer"}  # dual-write hook fired
      response:
        subsystems_invoked: [contemplator]
        ui_directives: []
```

**Initial scenario library (T2.9 ships ~10):**
- 01 — Basic chat turn, no subsystems
- 02 — Pattern entry triggers signals dual-write
- 03 — Belief update through `memory.write_belief_update`
- 04 — Contemplator deep pass + Archivist async handoff
- 05 — Directive emission (`open_widget`)
- 06 — Plain-text fallback when Anthropic returns invalid JSON
- 07 — Circuit breaker open → outbox enqueue → drain on recovery
- 08 — Em-dash normalization (`Pattern --` → `Pattern —`)
- 09 — Cost cap exceeded mid-conversation
- 10 — Auth failure (401 without bearer token)

**Adding scenarios is the new bug-triage discipline:** "Helm did X weird thing" → first action is to write a scenario reproducing it. The fix lands when the scenario passes.

**Runs in CI** as part of the existing pytest job (T0.A4). New requirement: tests/simulations passes are mandatory for merge.

**ARCH gate.** Sets the behavioral regression contract.

---

### T2.8 — V2 Note

Schema reference doc explicitly cross-links to ADR-001 (typing), ADR-002 (migration reversibility), ADR-003 (deployment target — written in T4.4) at the top.

---

## Phase 3 — Integration + Launch Validation

Carried forward from v1. V2 additions:

### T3.1, T3.2 — V2 Notes

Tests in vitest. Parser test covers JSON / plain text / malformed; directive handler test covers each of the 7 actions plus unknown-action ignore.

### T3.3 — V2 Notes

- Per-widget Realtime subscriptions wrap in TanStack Query for caching + revalidation (or vanilla `useEffect` if the team chooses; ADR-001 path may inform)
- Loading and error states are required, not optional. PR review rejects widgets without them.

### T3.4 — V2 Notes — Critical

- Auth header (`Authorization: Bearer ${VITE_HELM_API_TOKEN}`) on every `/invoke` and `/events` request
- Correlation ID header (`x-correlation-id`) — generated per session, propagated on every request, displayed in the UI's debug panel for support
- SSE EventSource doesn't natively support headers — **V2 specifies switching to `fetch-event-source` library** (or a small custom EventSource polyfill) for header support. Document in PR.
- Connection indicator surfaces auth failures (401) distinctly from network failures

### T3.5 — V2 Validation Checklist Additions

Carry forward v1's checklist. V2 adds:

- [ ] Auth: `/invoke` returns 401 without bearer token
- [ ] CI: every PR in this batch passed CI green
- [ ] Tests: memory module ≥80% coverage, runtime ≥60% coverage, UI smoke tests pass
- [ ] Observability: every Helm response has a correlation_id traceable through structured logs from request → memory.write → Supabase POST
- [ ] Cost: 1 day of normal use stays under daily cap; cost log in `helm.cost` events
- [ ] Outbox: kill Supabase mid-conversation, verify writes queue; restore Supabase, verify drain
- [ ] Backup: backup script runs, produces a valid restorable file
- [ ] Auth boundary: non-Maxwell session cannot reach the runtime without token (manual curl test)
- [ ] Runbooks: at least one entry exists in `docs/runbooks/` for: API token rotation, Supabase outage, runtime OOM, cost cap exceeded, Anthropic API down, Ollama model missing, frontend cannot connect
- [ ] STOP gate compliance: every ARCH-tier PR has Architect review noted; every STOP-tier PR has Maxwell approval noted

---

## Phase 4 — Operational Readiness

Phase 4 closes T1. This phase makes the launched system supportable.

---

### T4.1 — Runbook Set

**What:** Author the initial runbook library in `docs/runbooks/`.

**Required runbooks (10):**

| # | Title | Trigger |
|---|---|---|
| 0001 | API token rotation | Periodic / suspected leak |
| 0002 | Supabase backup + restore | Done in T0.A10, refined here |
| 0003 | Supabase outage / connection failure | Circuit breaker open in logs |
| 0004 | Runtime container OOM / crash | Container restart loop |
| 0005 | Anthropic API down | `helm.agent.prime` errors spike |
| 0006 | Ollama model missing or refused | `model_router` errors |
| 0007 | Frontend cannot connect | `DISCONNECTED` indicator persistent |
| 0008 | Cost cap exceeded | `cost.cap_exceeded` log event |
| 0009 | Outbox dead-letter accumulating | `/health` reports non-zero dead letter |
| 0010 | Schema migration failure | `supabase db push` fails |

**Format (each runbook):**
- Symptom (what the user / operator sees)
- Quick check (one-line command or query that confirms it's this issue)
- Diagnosis steps
- Fix steps
- Root cause considerations
- Links to relevant code, ADRs, or upstream docs

**STOP gate.**

---

### T4.2 — Rate Limiting on /invoke

**What:** Token-bucket rate limit per `HELM_API_TOKEN` (or per IP if no token). Default 60 requests/minute, burst 10.

**Library:** [`slowapi`](https://github.com/laurentS/slowapi) — FastAPI-native, simple, in-memory bucket (single-process; sufficient for T1).

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=lambda req: req.headers.get("authorization", get_remote_address(req)))
app.state.limiter = limiter

@app.post("/invoke/{agent_role}")
@limiter.limit("60/minute")
async def invoke_agent(...): ...
```

**429 response includes `Retry-After` header.**

**Configurable** via `HELM_RATE_LIMIT` env var (default `60/minute`).

**STOP gate.**

---

### T4.3 — SSE Session Resumption

**What:** UI may disconnect from `/events`. On reconnect, SSE specifies `Last-Event-ID` header — server replays missed events.

**Implementation:**
- Server-side: ring buffer per client session (in-memory, last 100 events). Each event has incrementing `id` field.
- Client sends `Last-Event-ID: <id>` on reconnect; server replays events with `id > last_event_id` from buffer.
- If buffer doesn't have it (overflowed), server sends a `replay_unavailable` event and the client knows to refresh state from Supabase.

**ARCH gate.** Affects the SSE contract; coordinate with T1.7 spec.

---

### T4.4 — Dev Deployment Decision (ADR-003)

**What:** Document the T1 deployment target. Three paths considered:

**Path A — Localhost-only at T1.** Helm runs via `docker compose` on Maxwell's machine. Deployment beyond localhost is Stage 2 work. Pro: zero hosting cost, zero ops surface. Con: laptop sleep kills Helm; no remote access; cannot reach from phone or other devices; T2 (scheduled) and T3 (ambient) work later requires re-architecting onto a 24/7 host anyway.

**Path B — Persistent dev deployment on free-tier hosts.** Vercel for UI (Maxwell already has account), Render free tier for runtime, existing Supabase free tier with `project` column partitioning for per-PR isolation. Pro: 24/7 stable URL; reachable from any device; future-proofs T2/T3; $0/month cost. Con: Render cold-start (~30s after 15min idle) — mitigated by warmup cron; 750 hrs/mo Render budget tight for always-on.

**Path C — Paid isolated stack.** Fly.io ($5/mo runtime) + Supabase Pro ($25/mo branching). Pro: no cold start, fully isolated per-PR DBs. Con: $30/mo at zero users.

**My recommendation:** **Path B** for T1. Cost-controlled while solo-dev; sets up the deployment shape for T2/T3 ambient work; trade-offs (cold start, shared dev Supabase) are acceptable for single-user use. Path C is the Stage 2 upgrade when Helm has users beyond Maxwell.

**ADR-003** records the decision. Path C config and migration path documented in `docs/runbooks/0011-deployment-paid-stack.md` so the upgrade is one PR away when Maxwell decides to spend.

T4.11 implements Path B.

**STOP gate.**

---

### T4.11 — Persistent Dev Deployment (ARCH)

**Purpose:** Implements Path B from ADR-003. Deploys `main` to a stable, always-on URL so Maxwell can talk to dev Helm from any device, and so T2/T3 (scheduled, ambient) work later has a 24/7 host already in place. This is **where dev Helm lives** between merges.

**Stack (all-free):**
- **UI:** Vercel — connect `helm-ui/` directory of the repo to Maxwell's existing Vercel account, auto-deploys on push to `main`. Stable URL: `helm.vercel.app` (or chosen subdomain).
- **Runtime:** Render free tier — `services/helm-runtime/Dockerfile` deployed from `main`, exposed at `helm-dev.onrender.com`. Free tier budget: 750 instance hours/month (24/7 = 720 hrs — fits, with ~30 hrs headroom).
- **Database:** Supabase free tier (existing project `zlcvrfmbtpxlhsqosdqf`). Dev runtime uses normal `project="hammerfall-solutions"` partition.
- **Secrets:** Set in Vercel + Render dashboards once. `VITE_HELM_API_URL` (UI → runtime), `VITE_SUPABASE_*`, `HELM_API_TOKEN`, `SUPABASE_BRAIN_SERVICE_KEY`, `ANTHROPIC_API_KEY`, etc.

**Render cold-start mitigation.** Free tier spins down after 15 min idle; cold start ~30s. Mitigation: GitHub Actions warmup cron every 10 min hits `/health`. Cost: ~4,300 cron invocations/month — well under GitHub Actions' 2,000 free minutes (each invocation is <5s).

**`.github/workflows/dev-warmup.yml`:**

```yaml
name: Dev Warmup
on:
  schedule:
    - cron: '*/10 * * * *'   # every 10 minutes
  workflow_dispatch:

jobs:
  warmup:
    runs-on: ubuntu-latest
    steps:
      - run: curl -sf https://helm-dev.onrender.com/health || exit 0
        # exit 0 even on failure — warmup is best-effort, T4.7 health checks own alerting
```

**Vercel deploy:** zero workflow code. Connect repo in Vercel dashboard → set root directory to `helm-ui/` → Vercel auto-deploys on push to `main`. PR previews come for free (used by T4.6).

**Render deploy:** `render.yaml` in repo root:

```yaml
services:
  - type: web
    name: helm-dev
    runtime: docker
    dockerfilePath: services/helm-runtime/Dockerfile
    branch: main
    healthCheckPath: /health
    plan: free
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false   # set in dashboard
      - key: SUPABASE_BRAIN_URL
        value: https://zlcvrfmbtpxlhsqosdqf.supabase.co
      - key: SUPABASE_BRAIN_SERVICE_KEY
        sync: false
      - key: HELM_API_TOKEN
        sync: false
```

**Decision points** (handled in T4.11 PR):
- Vercel project setup (one-time dashboard config; document in runbook for repeatability).
- Render account creation + GitHub repo connection.
- Render service plan (free) — confirm 750-hr budget math against T2/T3 future cron load.
- Subdomain choice for both Vercel and Render — affects what Maxwell types into his phone.

**Out of scope (Stage 2):**
- Custom domain + Let's Encrypt (Path C, runbook 0011).
- Render paid plan ($7/mo) if 750-hr budget is exceeded by T2/T3 cron volume.
- Multi-region deployment.

**ARCH gate.** Adds Vercel + Render as deployment dependencies. Maxwell sign-off needed on subdomain choice and Render account.

---

### T4.6 — Preview Environments per PR (ARCH)

**Purpose:** Helm changes are hard to evaluate from a diff. T4.6 spins up a per-PR runtime + UI so Maxwell can talk to the changed Helm before merging. This is the highest-leverage CI/CD investment for a behavior-driven product. Reuses the stack from T4.11 (Vercel + Render + Supabase) with ephemeral instances per PR.

**Stack (all-free, reuses T4.11):**
- **UI:** Vercel native PR previews — zero workflow code. Vercel auto-creates a preview URL for every PR when the repo is connected (already done in T4.11). URL pattern: `helm-ui-git-<branch>-<account>.vercel.app`. Auto-destroyed on PR close.
- **Runtime:** Render per-PR services — created via Render API on PR open, destroyed on PR close. URL pattern: `helm-pr-<num>.onrender.com`. Each is its own free-tier instance; cold start applies but acceptable for review use.
- **Database:** Supabase **project-column partitioning** on the existing free-tier project — no Supabase branching ($25/mo Pro required), no separate DB. The runtime's `project` column is set to `hammerfall-pr-<num>` for the preview env. `helm_memory`, `helm_frames`, `helm_messages` rows for that PR are isolated by query filter. Cleanup: `DELETE FROM helm_memory WHERE project = 'hammerfall-pr-<num>'` on PR close.

**Open question for T4.6 PR:** Per-table partition policy. Some tables are Helm's identity (shared across all PRs — `helm_personality`, `helm_beliefs`, `helm_entities` if they exist by then). Others are per-conversation (partition by `project` — `helm_memory`, `helm_frames`, `helm_messages`). T4.6 PR enumerates which tables get which treatment, with rationale. Default: anything with a `project` column gets partitioned; identity tables shared.

**`.github/workflows/preview.yml` (sketch):**

```yaml
name: PR Preview
on:
  pull_request:
    types: [opened, synchronize, reopened, closed]

jobs:
  deploy-runtime:
    if: github.event.action != 'closed'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create or update Render service for PR
        run: |
          curl -X POST https://api.render.com/v1/services \
            -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{
              "type": "web_service",
              "name": "helm-pr-${{ github.event.pull_request.number }}",
              "repo": "https://github.com/${{ github.repository }}",
              "branch": "${{ github.head_ref }}",
              "plan": "free",
              "envVars": [
                {"key": "HELM_PROJECT_PARTITION", "value": "hammerfall-pr-${{ github.event.pull_request.number }}"}
              ]
            }'
      - name: Comment PR with URLs
        uses: thollander/actions-comment-pull-request@v2
        with:
          message: |
            Preview runtime: https://helm-pr-${{ github.event.pull_request.number }}.onrender.com
            Preview UI: (Vercel auto-provisions — see Vercel bot comment)

  teardown:
    if: github.event.action == 'closed'
    runs-on: ubuntu-latest
    steps:
      - name: Destroy Render service
        run: |
          curl -X DELETE \
            "https://api.render.com/v1/services/helm-pr-${{ github.event.pull_request.number }}" \
            -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}"
      - name: Clean up Supabase partition data
        env:
          SUPABASE_BRAIN_SERVICE_KEY: ${{ secrets.SUPABASE_BRAIN_SERVICE_KEY }}
        run: |
          PARTITION="hammerfall-pr-${{ github.event.pull_request.number }}"
          for table in helm_memory helm_frames helm_messages; do
            curl -X DELETE \
              "https://zlcvrfmbtpxlhsqosdqf.supabase.co/rest/v1/${table}?project=eq.${PARTITION}" \
              -H "apikey: $SUPABASE_BRAIN_SERVICE_KEY" \
              -H "Authorization: Bearer $SUPABASE_BRAIN_SERVICE_KEY"
          done
```

**Cost considerations:** Each preview env consumes ~30 hrs/PR if open for a few days (Render free tier shared budget with T4.11 dev deployment — the 750-hr cap is per-account, not per-service). With single-dev sequential execution, 1–2 open PRs at a time means ~60 hrs/month preview load on top of T4.11's 720 hrs persistent — comfortably within budget. Vercel previews and Supabase partition data are free.

**Limit per dev:** Single-dev model means at most 1–2 open PRs at a time. If preview cap becomes a constraint, paid Render upgrade ($7/mo) lifts the per-account hour cap.

**ARCH gate.** Reuses Vercel + Render + Supabase from T4.11 (no new deployment dependencies). Adds project-column partition convention.

---

### T4.7 — Scheduled Health Checks

**Purpose:** Operational eyes when Maxwell isn't looking. Cron-driven workflow hits `/health` and a canary `/invoke`. On failure, opens or comments on a tracking issue with diagnostic details.

**`.github/workflows/health-check.yml`:**

```yaml
name: Scheduled Health Check
on:
  schedule:
    - cron: '*/15 * * * *'   # every 15 minutes
  workflow_dispatch:

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - name: /health probe
        id: health
        run: |
          curl -f -s --max-time 10 \
            -H "Authorization: Bearer ${{ secrets.HELM_API_TOKEN }}" \
            ${{ secrets.HELM_BASE_URL }}/health | tee health.json
        continue-on-error: true

      - name: Canary /invoke probe
        id: canary
        run: |
          curl -f -s --max-time 30 \
            -H "Authorization: Bearer ${{ secrets.HELM_API_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"user_message":"healthcheck-canary","session_id":"00000000-0000-4000-8000-000000000001","turn_number":0}' \
            ${{ secrets.HELM_BASE_URL }}/invoke/helm_prime | tee canary.json
        continue-on-error: true

      - name: Open / update issue on failure
        if: steps.health.outcome == 'failure' || steps.canary.outcome == 'failure'
        uses: jayqi/failed-build-issue-action@v1
```

**Probe definition:**
- `/health` must return 200 with `{status: "healthy"}` and all 4 agents reporting healthy
- Canary `/invoke` must return 200 with parseable JSON in `<30s`
- Three consecutive failures escalate (issue gets a `urgent` label) — single failures may just be transient network

**Canary message:** Hardcoded `healthcheck-canary` string. Helm's prompt gets a one-line addition (in T4.7 PR): "If you receive `healthcheck-canary` as a user message, respond with `pong` and no subsystems. Do not write to memory." This keeps health checks free of Helm's normal cognitive overhead and zero-cost in memory writes.

**STOP gate.**

---

### T4.8 — Performance Regression Baseline + Bench

**Purpose:** Establish the "Helm is fast enough" baseline and detect when it isn't. Single metric for T1: end-to-end latency on a fixed input set. p50, p95, p99.

**`services/helm-runtime/tests/bench/`** holds:
- `inputs.yaml` — 20 canned messages (5 each of: short chat, deep contemplator pass, directive emission, memory query)
- `bench.py` — runs each input N times, captures latency, writes results to `bench-results-<sha>.json`
- `compare.py` — diffs current run against baseline; fails if p95 regressed >20% on any input class

**Workflow:**

```yaml
name: Performance Bench
on:
  pull_request:
    paths:
      - 'services/helm-runtime/**'
      - 'agents/helm/helm_prompt.md'
  workflow_dispatch:

jobs:
  bench:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Boot runtime in bench mode
        run: docker compose -f services/helm-runtime/docker-compose.bench.yml up -d
      - name: Run bench
        run: python services/helm-runtime/tests/bench/bench.py --output bench-current.json
      - name: Compare against baseline
        run: python services/helm-runtime/tests/bench/compare.py bench-current.json supabase/bench-baseline.json
      - name: Comment PR with bench delta
        uses: thollander/actions-comment-pull-request@v2
        with:
          message: |
            Bench results vs baseline:
            ${{ steps.compare.outputs.summary }}
```

**Baseline establishment:** First run on `main` after T4.8 lands writes the baseline. Updated periodically (Maxwell's call — typically when an intentional perf optimization or expected regression lands).

**Mocked Anthropic in bench mode** — bench measures Helm's overhead, not Anthropic's response time. Same mocking infrastructure as T2.9.

**STOP gate.**

---

### T4.9 — Docs Site Auto-Deploy

**Purpose:** V2 spec, ADRs, runbooks browseable as a rendered site. Cheap operational visibility for Maxwell ("what's the runbook for X?" → `helm-docs.pages.dev/runbooks/0008`).

**Stack:** [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) — Python-based, dead-simple config, beautiful default theme, live search, deploys static HTML to GitHub Pages.

**`mkdocs.yml`:**

```yaml
site_name: Helm Docs
nav:
  - Home: index.md
  - V2 Spec: stage1/Helm_T1_Launch_Spec_V2.md
  - ADRs:
      - Index: adr/index.md
  - Runbooks:
      - Index: runbooks/index.md
  - Founding:
      - Vision: founding_docs/Helm_The_Ambient_Turn.md
      - Roadmap: founding_docs/Helm_Roadmap.md
theme:
  name: material
  features: [navigation.instant, navigation.sections, content.code.copy, search.highlight]
docs_dir: docs
```

**`.github/workflows/docs.yml`:**

```yaml
name: Docs
on:
  push:
    branches: [main]
    paths: ['docs/**', 'mkdocs.yml']
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: github-pages
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install mkdocs mkdocs-material
      - run: mkdocs build
      - uses: actions/upload-pages-artifact@v3
        with: { path: site/ }
      - uses: actions/deploy-pages@v4
```

**No content rewrite required.** MkDocs ingests existing markdown as-is. ADR and runbook indexes are auto-generated from directory listings via a small mkdocs plugin or a hand-maintained `index.md` per directory.

**Privacy:** GitHub Pages is public. The repo is currently public, so this is consistent. If the repo flips private, the docs site flips too (GitHub Pages on private repos requires Pro tier — Maxwell's call at that point).

**Batch tier.** Bundles with T4.10 if both go in the same window.

---

### T4.10 — Release Automation

**Purpose:** When T1 closes (T4.5) and beyond, Helm should have versioned releases. Today there's no concept of "Helm v0.1.0" — every commit is the latest. Releases give:
- A reference point ("the bug appeared in v0.3.2, last worked in v0.3.1")
- A trigger for downstream consumers (notifications, image tags)
- An archival changelog future-Maxwell can read

**Stack:** [release-please](https://github.com/googleapis/release-please) — reads Conventional Commits (already required per T0.A1), generates changelogs, opens release PRs, tags + creates GitHub releases on merge.

**`.github/workflows/release.yml`:**

```yaml
name: Release Please
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: simple
          package-name: helm
```

**Behavior:**
- After every merge to `main`, release-please opens or updates a `release-please--branches--main` PR
- That PR's body contains the auto-generated changelog (grouped by Conventional Commit type)
- Merging that PR creates a git tag (`v0.X.Y`) and a GitHub release
- T0.A12's container build workflow tags the resulting image with the version

**Versioning policy:**
- T1 lands as `v0.1.0`
- Patch bumps: `fix` commits
- Minor bumps: `feat` commits
- Major bump (`v1.0.0`): Stage 1 closure — Maxwell decides when

**STOP gate.** Establishes versioning policy.

---

### T4.5 — Operational SITREP — T1 Close

**What:** Write `docs/stage1/SITREPs/t1-close-report.md`. Documents:
- Tasks completed (V2 task list with statuses)
- Architecture as-built (cross-link to ADRs)
- Known limitations carried forward to Stage 2
- Test coverage summary
- Performance baseline (latency p50/p95 on Helm Prime invoke, memory write throughput)
- Cost baseline (one week of normal use)
- Runbook inventory
- Backup status
- "What broke during Phase 0–4 that we fixed and how" section (institutional memory)

After this PR merges, T1 is closed. Stage 2 planning begins.

**STOP gate.**

---

## T0 Impact on Downstream Phases (Same as v1)

| Original Task | Impact from T0 |
|---|---|
| T2.1 (Prompt storage) | **Absorbed into T0.B5.** |
| T2.2 (Async handoff) | **Simplified.** Outbox provides durability. |
| T2.3 (SSE endpoint) | **Cleaner integration.** Emit hooks via observability layer. |
| T2.5 (Belief slugs) | **One slug utility** in `memory/models.py`, used by backfill + runtime. |
| T2.6 (Belief history) | **Single `memory.write_belief_update()` call.** |
| T2.7 (Signals) | **Dual-write hook in memory module** with transaction safety per V2 §T2.6. |
| T3.3 (Supabase integration) | **No change.** UI reads via anon key. |
| T3.4 (Runtime integration) | **Auth + correlation IDs added.** |

---

## Dependencies & Build Order

```
T0.A1 ─► T0.A2 ─► T0.A3 ─► T0.A4
                              │
T0.A5 (ADR-001) ──────────────┤
T0.A6 ────────────────────────┤
T0.A7 ──┬─────────────────────┤
        │
        └─► T0.A12 (container build, needs T0.A7) ──► T0.A13 ─► T0.A14
                                                                    │
T0.A9 (incl. CI migration safety) ──────────────────────────────────┤
T0.A8 ──────────────────────────────────────────────────────────────┤
T0.A10 ─────────────────────────────────────────────────────────────┤
T0.A11 ─┬───────────────────────────────────────────────────────────┘
        │
        └─► T0.A15 (cost summary, pairs with T0.A11)
                              │
                              ▼
                    T0.B1 ─► T0.B2 ─► T0.B3 ─► T0.B4 ─► T0.B5 ─► T0.B6
                              │
                              ▼
T1.1, T1.2, T1.3, T1.4, T1.5a, T1.5b, T1.6 ─► T1.7 (HARD GATE)
                                                  │
                                                  ▼
                                       T2.2 ─► T2.3 ─► T2.9 (needs T2.3) ─► T2.4 ─► T2.5 ─► T2.6 ─► T2.7 ─► T2.8
                                                  │
                                                  ▼
                                       T3.1, T3.2 (after T2.3)
                                       T3.3 (after T2.4–T2.7)
                                       T3.4 (after T0.A8 + T2.3)
                                       T3.5 (after T3.1–T3.4)
                                                  │
                                                  ▼
                                       T4.1 ─► T4.2 ─► T4.3 ─► T4.4 (ADR-003)
                                                                  │
                                                                  ▼
                                       T4.11 (persistent dev deployment, implements ADR-003)
                                                                  │
                                                                  ▼
                                       T4.6 (preview envs, reuses T4.11 stack)
                                       T4.7 (health checks, needs T4.11 deployed instance)
                                       T4.8 (perf bench, needs T4.11 deployed instance)
                                       T4.9 (docs site)
                                       T4.10 (release automation)
                                                                  │
                                                                  ▼
                                                              T4.5 (T1 close SITREP)
```

---

## Risk Register

| Risk | Phase | Mitigation |
|---|---|---|
| LiteLLM `cache_control` pass-through breaks | T2.3 | Verify at impl time; pin LiteLLM version; fallback to direct Anthropic SDK call if needed |
| TypeScript conversion (if ADR-001 Path A) blows up T1.5b scope | T1.5b | Bundle is the right call; if scope explodes, split TS conversion into its own PR before T1.5b |
| SQLite outbox doesn't handle high write rate | T0.B2 | At T1 scale (single user, single agent set), well within SQLite's envelope. Stage 2 considers Postgres-backed if needed. |
| Supabase Realtime drops connection mid-Phase-3 validation | T3.5 | T4.3 (session resumption) is in Phase 4 *after* T3.5. If Realtime drops repeatedly during T3.5, advance T4.3 ahead of T3.5. |
| Anthropic prompt cache TTL (5 min) doesn't help one-off turns | T2.3 | Acceptable. T2 scheduled work + T3 ambient work will keep sessions warm. |
| Cost cap of $5/day is too low for normal use | T0.A11 | Configurable; raise after first week of observation. Initial cap is paranoia, not policy. |
| Backup runbook drill reveals Supabase tier doesn't allow `pg_dump` | T0.A10 | Use Supabase Dashboard backup feature instead; document the alternate path in the runbook |
| `pre-commit install` doesn't run in Windows / WSL transition | T0.A2 | Document in `AGENTS.md`; CI catches what hooks miss |
| ADR-001 Path A discovers helm-ui is too JSX-coupled to convert cleanly | T0.A5 | ADR captures the discovery; flip to Path B; T1.5b reverts to JSX scope |
| Memory module 80% coverage target too aggressive for T0.B1 | T0.B1 | Coverage is a target, not a gate. PR can ship at lower coverage with explicit deferred-coverage list. |
| GHCR container size grows beyond free tier | T0.A12 | Multi-stage Dockerfile already trims; if hit, prune old image tags via scheduled workflow |
| Gitleaks false positives on Supabase anon key | T0.A13 | `.gitleaks.toml` allowlist with comment-rationale |
| Dependabot opens too many PRs | T0.A14 | Grouping config + open-pull-requests-limit:5; disable if it becomes noise |
| Render account / Vercel project setup blocks T4.11 | T4.11 | T4.11 PR description identifies blockers; Vercel account already exists (Maxwell). Render signup is free + fast. |
| Render free-tier 750-hr/month cap exceeded by T4.11 + T4.6 + T2/T3 cron load | T4.11, T4.6 | T4.11 budgets 720 hrs persistent; T4.6 adds ~60 hrs/month at 1–2 open PRs. Headroom is thin. Mitigation: scale-to-zero on preview envs, monitor monthly via Render dashboard. Upgrade to $7/mo paid plan if cap hit. |
| Render cold-start (~30s after 15min idle) frustrates Maxwell when checking from phone | T4.11 | Warmup cron every 10 min keeps the instance hot during waking hours. Cold start still possible after long idle (overnight); acceptable trade-off vs $7/mo paid. |
| Supabase project-column partition data orphaned if PR closes without teardown workflow run | T4.6 | Cleanup workflow runs on PR close event; if it fails, scheduled monthly sweep deletes any `project LIKE 'hammerfall-pr-%'` rows older than 30 days. Documented in runbook. |
| Per-PR partition policy ambiguous for identity tables (helm_personality, helm_beliefs) | T4.6 | T4.6 PR enumerates per-table policy with rationale. Default: shared identity, partitioned conversation. |
| Vercel project setup tied to Maxwell's account creates bus factor | T4.11 | Documented in runbook: how to re-create Vercel project + reconnect repo if account access lost. Acceptable for solo-dev T1. |
| Bench results too noisy on shared-runner CI | T4.8 | Run N=20 per input, use median; or self-hosted runner if noise persists |
| MkDocs build fails on emoji or wide table in markdown | T4.9 | Standard MD-to-HTML; rare. PR catches at first build. |
| release-please opens unmerged release PRs that pile up | T4.10 | Documented in runbook 0012 (added in T4.10): "merge release PRs at end of work cycle" |
| Agent simulation harness becomes brittle to prompt edits | T2.9 | Scenarios assert behavior shape, not exact text. Prompt edit that doesn't change shape passes. |

---

## What V2 Does NOT Cover (Stage 2+)

These were considered and explicitly deferred:

- **Multi-user auth** — single-user, single bearer token at T1. Real auth (OAuth, SSO, per-user identity) is Stage 2.
- **Cross-device session identity** — per-device sessions stored in `localStorage` at T1. Cross-device requires user identity (above).
- **Per-user RLS policies** — anon read on all brain tables at T1 (already in place). Per-user policies require user identity.
- **Horizontal scaling** — single-process FastAPI at T1. Stage 2 considers gunicorn workers, then container orchestration.
- **Production secrets manager** — `.env` at T1. Stage 2 evaluates 1Password/Vault/SOPS based on deployment target.
- **CDN, edge caching** — Vite static build served by container at T1.
- **Distributed tracing across services** — OpenTelemetry primitives in place at T1, exporter (Jaeger/Tempo) in Stage 2.
- **Anthropic cost cap** — only embedding cap at T1; Anthropic spend is logged but not capped.
- **Automated backup rotation** — manual cron at T1; automation is Stage 2.
- **Sentry / error aggregation service** — structured logs at T1; aggregation is Stage 2.
- **Performance profiling / APM beyond latency bench** — T4.8 covers latency regression; full APM (flame graphs, span breakdowns, memory profiling) is Stage 2.
- **Multi-environment (dev / staging / prod)** — single environment at T1; PR previews (T4.6) are ephemeral, not a staging tier.
- **Disaster recovery beyond `pg_dump`** — point-in-time recovery via Supabase tier in Stage 2.
- **GitHub Advanced Security / SAST** — paid GitHub feature, overkill for solo project. T0.A13 (gitleaks) covers the secret-leak risk; CodeQL / Snyk-style SAST is Stage 2 if/when Helm becomes multi-user.
- **Multi-OS test matrix** — T1 deploys to Linux containers only. CI runs on Linux. Adding Windows/macOS runners adds time and surface area for negative ROI at T1. Stage 2 if Helm gains a desktop-distributed component.
- **Auto-merge of Dependabot PRs** — T0.A14 ships the config; auto-merge is opt-in per Maxwell's preference. Default is manual review.
- **Self-hosted CI runners** — GitHub-hosted runners at T1. Self-hosted considered in Stage 2 if Render / Vercel egress costs make CI flow expensive.
- **Per-PR cost reports** — T0.A15 is weekly aggregate. Per-PR cost projection is Stage 2.

---

## Appendix A — PR Description Template

Every PR uses this template. Lives at `.github/pull_request_template.md` (added in T0.A1).

```markdown
## What

One-line description of what this PR does.

## Task ID(s)

V2 task IDs implemented or partially implemented (e.g., T0.B1, T0.B2).

## Why

Why this change is needed. Cross-link to spec, ADR, or runbook.

## How

Brief implementation summary. Cross-link to non-obvious decisions.

## Testing

- [ ] CI green
- [ ] New code has tests
- [ ] Manual smoke test described below

Manual smoke test:
<commands run, expected output>

## STOP gate tier

[Full STOP / STOP / Batch] — see V2 spec §STOP gate discipline

## Maxwell post-merge checklist

- [ ] (e.g., enable Realtime on new table)
- [ ] (e.g., update branch protection)
- [ ] (e.g., regenerate API token)

## Out of scope (deferred)

Anything noticed but not addressed; cross-link to follow-up issue or new task.
```

---

## Appendix B — ADR Index

ADRs created during V2 execution:

| ID | Title | Created in | Status |
|---|---|---|---|
| ADR-001 | helm-ui type discipline (TS conversion vs JSDoc + ESLint strict) | T0.A5 | Pending |
| ADR-002 | Migration reversibility policy | T0.A9 | Pending |
| ADR-003 | T1 deployment target (localhost vs persistent dev free vs paid isolated) | T4.4 | Pending — V2 recommends Path B (Vercel + Render + Supabase project partition) |
| ADR-004 | Anthropic vs LiteLLM for prompt caching pass-through | T2.3 | Conditional — only if LiteLLM doesn't pass through |
| ADR-005 | GHCR public vs private image visibility | T0.A12 | Pending |
| ADR-006 | Dependabot vs Renovate for dependency automation | T0.A14 | Pending — V2 picks Dependabot, ADR records the rejected option |
| ADR-007 | PR preview stack (Vercel native previews + Render per-PR + Supabase project-column partitioning) | T4.6 | Pending — all-free stack, reuses T4.11 deployment dependencies |
| ADR-008 | Versioning policy + release-please configuration | T4.10 | Pending |
| ADR-009 | (placeholder for any architectural decision discovered during execution) | — | — |

---

## Appendix C — Runbook Index

Runbooks created during V2 execution:

| ID | Title | Created in |
|---|---|---|
| 0000 | Template | T0.A1 |
| 0001 | API token rotation | T0.A8 |
| 0002 | Supabase backup + restore | T0.A10 |
| 0003 | Supabase outage / circuit breaker open | T4.1 |
| 0004 | Runtime container OOM | T4.1 |
| 0005 | Anthropic API down | T4.1 |
| 0006 | Ollama model missing | T4.1 |
| 0007 | Frontend disconnected | T4.1 |
| 0008 | Cost cap exceeded | T4.1 |
| 0009 | Outbox dead-letter accumulating | T4.1 |
| 0010 | Schema migration failure | T4.1 |
| 0011 | Deployment via paid isolated stack — Fly.io + Supabase Pro (deferred to Stage 2) | T4.4 |
| 0012 | Release PR management (release-please workflow) | T4.10 |
| 0013 | Preview environment teardown / Supabase project-partition orphan cleanup | T4.6 |
| 0014 | Bench baseline reset procedure | T4.8 |
| 0015 | Container image pruning (GHCR storage management) | T0.A12 |
| 0016 | Dependabot grouping rules + skip rationale | T0.A14 |
| 0017 | Persistent dev deployment — Vercel project setup + Render service config + warmup cron management | T4.11 |

---

## Appendix D — V1 Issues Resolved by V2

Direct mapping of v1 issues raised in the comprehensive review to V2 task that resolves them.

| V1 issue | V2 resolution |
|---|---|
| `supabase_client.py` docstring canonizes the brain.sh divergence | T0.B6 — rewrites docstring + renames file to `read_client.py` |
| JSONL outbox concurrency race | T0.B2 — SQLite outbox replaces JSONL |
| Narrow MemoryType enum (no FRAME, BELIEF_UPDATE, etc.) | T0.B1 — expanded enum |
| Em-dash unicode coupling for "Pattern —" | T0.B6 — write-time normalization |
| Circuit breaker has no observability | T0.B1 — emits state-change events; T2.3 wires to SSE |
| 12+ scattered `emit_event` calls in main.py | T2.3 — moved into hook decorators + post-write hooks |
| Misleading commit message risk | T0.A1 + T0.A2 — Conventional Commits + commitlint |
| Atomic write uses `Path.rename` (not Windows-safe) | T0.B4 — uses `os.replace` |
| `/tmp` outbox path not portable | T0.B1 — `Path.home() / .helm` default |
| `datetime.utcnow()` deprecated | T0.B1 — UTC-aware `utc_now()` helper |
| Four prompt/doc files still encode brain.sh paradigm | T0.B6 expanded scope to all four |
| No vendor-neutral agent operating contract | T0.A1 — `AGENTS.md` |
| No tests directory | T0.A3 |
| No CI | T0.A4 |
| No type checking | T0.A5 |
| No structured logging convention | T0.A6 |
| No correlation IDs | T0.A6 |
| Dockerfile builds as root, no HEALTHCHECK | T0.A7 |
| No API auth | T0.A8 |
| No migration discipline / baseline | T0.A9 |
| No backup procedure | T0.A10 |
| No cost guardrails | T0.A11 |
| No runbooks | T0.A1 (template) + T4.1 (set) |
| No rate limiting | T4.2 |
| No SSE session resumption | T4.3 |
| Deployment target undecided | T4.4 (ADR-003 — recommends persistent dev free stack) |
| No persistent dev deployment for 24/7 access from any device | T4.11 — Vercel + Render + Supabase, stable URL, all-free stack |
| Dual-write transaction safety unspecified | T2.6 V2 notes — explicit semantics + outbox retry |
| `subsystems_invoked` semantics underspecified | T1.7 V2 notes — locked in spec + tested in T1.1 |
| No agent behavior regression net | T2.9 — agent simulation harness with 10 scenarios |
| No container artifact pipeline | T0.A12 — GHCR build + publish on every merge |
| No accidental-secret commit protection | T0.A13 — gitleaks on every push |
| No dependency upgrade discipline | T0.A14 — Dependabot grouped weekly PRs |
| No spend visibility (only the cap) | T0.A15 — weekly cost summary issue |
| No ephemeral environment for behavior review | T4.6 — per-PR runtime + UI + Supabase project-column partition (all-free) |
| No external operational signal | T4.7 — scheduled health + canary checks |
| No latency regression detection | T4.8 — perf bench on PRs that touch runtime / prompt |
| No browseable docs surface | T4.9 — MkDocs site auto-deployed to GitHub Pages |
| No version concept / changelog | T4.10 — release-please + Conventional-Commit-driven releases |
| No CI migration safety net | T0.A9 enhanced — ephemeral Supabase branch + reversibility check |

---

## Maxwell Sign-off (V2)

By merging this PR, Maxwell agrees:

- V2 supersedes v1 as the canonical T1 build spec
- The execution order in §Execution Order is the agreed-upon sequence (changes go through STOP gates)
- Single-dev (Helm IDE / me) executes; Maxwell reviews at every STOP gate; Architect consulted on ARCH-tier tasks
- The 49–57 PR count is the realistic shape of "T1 close on a solid foundation with full CI/CD + persistent dev deployment"
- T1 close = `T4.5` SITREP merged; not before

V2 is a contract between Maxwell and the dev. Where reality forces deviation, the deviation is documented (PR description or new ADR), not silently absorbed.
