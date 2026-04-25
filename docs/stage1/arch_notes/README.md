# Arch-tier design notes

Pre-build one-pagers for every ARCH-tier task in the V2 spec. The architect reviews each before the corresponding task starts; reviews happen at task boundaries (not per-PR), turning him into a structural participant on shape decisions instead of a passenger on syntax.

## How this works

- One file per ARCH-tier task (`T<n>.md`).
- Authored ahead of time so the architect can spot inconsistencies across the arc, not just per-task.
- Refreshed (small update, not rewrite) immediately before the task starts, in case the surrounding context has shifted.
- Architect green-lights or pushes back; if pushback, this doc is amended and re-circulated before build.
- During the build, the corresponding PR opens with a SITREP that notes any deviations from this design note.

## The 10 ARCH-tier tasks

| # | Task | Phase | One-pager |
|---|---|---|---|
| 1 | T0.A7 — Deployment Hardening | 0A | [T0.A7_deployment_hardening.md](T0.A7_deployment_hardening.md) |
| 2 | T0.A8 — API Auth | 0A | [T0.A8_api_auth.md](T0.A8_api_auth.md) |
| 3 | T0.A12 — CI: Container Build + GHCR Publish | 0A | [T0.A12_ci_container_build.md](T0.A12_ci_container_build.md) |
| 4 | T0.B1 — Memory Module Core | 0B | [T0.B1_memory_module_core.md](T0.B1_memory_module_core.md) |
| 5 | T0.B2 — Outbox Pattern | 0B | [T0.B2_outbox_pattern.md](T0.B2_outbox_pattern.md) |
| 6 | T0.B3 — Migrate In-Process Agents | 0B | [T0.B3_migrate_in_process_agents.md](T0.B3_migrate_in_process_agents.md) |
| 7 | T0.B7 — Tier 2 Brain Types | 0B | [T0.B7_tier2_brain_types.md](T0.B7_tier2_brain_types.md) |
| 8 | T2.9 — Agent Simulation Test Harness | 2 | [T2.9_agent_simulation_test_harness.md](T2.9_agent_simulation_test_harness.md) |
| 9 | T4.6 — Preview Environments per PR | 4 | [T4.6_preview_environments_per_pr.md](T4.6_preview_environments_per_pr.md) |
| 10 | T4.11 — Persistent Dev Deployment | 4 | [T4.11_persistent_dev_deployment.md](T4.11_persistent_dev_deployment.md) |

## Review cadence

Architect reviews these one-pagers as a single batch first (now), then re-confirms each immediately before the corresponding task starts. STOP-tier tasks within these (notably T0.B7 has a STOP gate after the third sub-PR) also require Maxwell sign-off at the gate per existing spec convention.

## Tasks not in this list

Tasks marked IMPL-tier in the V2 spec do not have one-pagers. Those proceed under standard PR-level review. The boundary between ARCH and IMPL is set in the V2 spec at task definition time and is not relabeled mid-build.

## Template structure

Each one-pager follows the same shape so the architect knows where to look:

1. **What I'm building** — 1-2 sentences.
2. **Why this shape** — the architectural choice + reasoning.
3. **Alternatives considered + rejected** — what was ruled out and why.
4. **Interfaces / contracts** — what other tasks depend on this.
5. **Risks + open questions for architect** — explicit points for review.
6. **What "done" looks like at the gate** — acceptance criteria.

## Architect review — 2026-04-24

All 10 one-pagers approved. Per-task decisions captured in each one-pager's `## Architect review` section. Cross-cutting observations from the review:

1. **Dependency chain is clean.** T0.A (repo/ops) → T0.B (memory) → T1 (UI) → T2 (backend) → T3 (integration) → T4 (ops readiness). No circular dependencies; no task that depends on something in a later phase.
2. **The T0.B7 abstraction validation is good engineering practice.** Using the first real consumer (new brain types) to validate the abstraction (memory module) before building more on top of it is the kind of discipline that prevents "we built the wrong abstraction and now everything depends on it."
3. **Phase 0A is psychologically heavy.** ~15 tasks of repo infrastructure (CI, Docker hardening, API auth, migration discipline, backup runbooks, cost guardrails) before any product-visible Helm behavior change. Correct engineering practice; trust the process. The payoff is that every subsequent PR lands on solid ground.
4. **Free-tier constraint is well-managed.** Vercel hobby + Render free + Supabase free + GitHub Actions free. The math works for single-dev T1. The $7/mo Render escape hatch is documented. Cost cap (T0.A11) protects against runaway API spend.

**Next:** T0.A1 first, per the V2 spec execution order. ARCH-tier tasks refresh their one-pager immediately before build and cite it in the PR's SITREP.

## Related

- [Helm_T1_Launch_Spec_V2.md](../Helm_T1_Launch_Spec_V2.md) — the canonical T1 spec these notes elaborate on.
- [Post_T1_Findings.md](../Post_T1_Findings.md) — the operational queue for deferrals surfaced during T1 execution.
- [docs/founding_docs/Helm_Brain_Object_Types.md](../../founding_docs/Helm_Brain_Object_Types.md) — the brain types catalog these notes reference.
