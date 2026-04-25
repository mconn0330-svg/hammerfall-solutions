# AGENTS.md — Operating Contract for Agents in This Repo

This file is the canonical, vendor-neutral instruction set for any agentic coding tool working in `hammerfall-solutions`. It is picked up natively by Claude Code, Cursor, Aider, Codex, and other tools that follow the emerging `AGENTS.md` convention. Do not branch this file by vendor; if a tool requires its own filename, add a one-line shim that points here.

## What this repo is

Hammerfall is the runtime + UI for Helm — an ambient AI presence Maxwell McConnell is building. T1 (the first launchable Helm) is currently being built per `docs/stage1/Helm_T1_Launch_Spec_V2.md`. That document is **canonical** for T1 work; if anything in this file conflicts with V2, V2 wins.

## Hard rules

1. **V2 spec is canonical.** When in doubt about scope, intent, or shape, read `docs/stage1/Helm_T1_Launch_Spec_V2.md` first. ARCH-tier tasks have additional design notes in `docs/stage1/arch_notes/`.

2. **Conventional Commits required.** Every commit message follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). `commitlint` enforces this locally (T0.A2) and in CI (T0.A4). Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`. Allowed scopes: `memory`, `runtime`, `ui`, `agent`, `prompt`, `infra`, `ci`, `docs`, `migration`, `repo`, `auth`, `obs`, `ops`. See `commitlint.config.js`.

3. **STOP gates are non-optional.** Any task tagged `STOP` in the V2 spec requires Maxwell's explicit approval before merge. Any task tagged `ARCH` requires the architect's approval of the matching one-pager in `docs/stage1/arch_notes/` before build starts. Do not relabel mid-build to skip a gate.

4. **Tests come with the code.** New code lands with tests. The test harness exists (T0.A3 → pytest for Python, vitest for JS). If you add behavior, add a test. If you fix a bug, add a regression test. T2.9 is the behavioral regression net for the runtime; bug repros land there as `tests/simulations/<scenario>.yaml`.

5. **Memory writes go through `memory.write()`.** Never call `supabase_client.insert/post` directly from agent code. Never invoke `brain.sh` (deleted at T0.B6 — references in any new code are a regression). Reads documented in T0.B3's disposition table; some still go through `read_client.py` (renamed at T0.B6) until Stage 2.

6. **Structured logging convention.** Use `structlog` with logger names of the form `helm.<module>` (e.g., `helm.memory.client`, `helm.agents.contemplator`). Every cross-component request carries a correlation ID. Logs are JSON-shaped — no `print()` statements in shipped code.

7. **Don't claim a PR is ready until CI is green.** "Looks good locally" is not sufficient. CI exists for this reason (T0.A4 onward).

## Soft rules — strong defaults

- **Single-dev sequential execution.** One PR at a time. No parallel branches without explicit reason.
- **Each PR opens with a SITREP** in `docs/stage1/SITREPs/`. Cite the matching task ID(s); flag out-of-scope items so they're not lost.
- **Founding docs stay global.** `docs/founding_docs/` is the canonical reference. Update there before referencing in spec or PR.
- **Found a problem outside the current task?** Append to `docs/stage1/Post_T1_Findings.md` with a Finding #NNN block. Reference the finding number in the PR's SITREP. Do not balloon the current task.
- **Don't gold-plate.** V2 is the floor and the ceiling for T1. New scope goes through Maxwell, not into a quiet PR.

## Where to look for known failures

`docs/runbooks/` — symptom → diagnosis → fix → root cause. If you hit something that should have a runbook and doesn't, add one (template at `docs/runbooks/0000-template.md`).

## When in doubt

Ask Maxwell. He's the sole human stakeholder; surfacing uncertainty early is cheaper than rebuilding work later.

---

**Maintenance:** This file is updated as the operating contract evolves (new conventions, new gates, etc.). Treat updates as ARCH-tier even though no `arch_notes/` one-pager exists for it — changes here ripple through every future contributor's behavior.
