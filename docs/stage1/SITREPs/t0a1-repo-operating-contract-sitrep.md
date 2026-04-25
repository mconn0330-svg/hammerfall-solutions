# SITREP — T0.A1 Repo Operating Contract

**Date:** 2026-04-25
**Branch:** `feature/t0a1-repo-operating-contract`
**Tier:** STOP
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.A1 (line 85, deliverables described §"Conventional Commits — Enforced" line 61)
**Arch note:** `docs/stage1/arch_notes/01-t0a1-repo-operating-contract.md` (architect-approved)

## Scope executed

T0.A1 lands the **rules of the road** for every subsequent task: a vendor-neutral
operating contract any agent (Claude Code, Cursor, Aider, Codex, future-Maxwell)
picks up automatically, the Conventional Commits enforcement config that T0.A2
consumes via pre-commit hook and T0.A4 consumes in CI, and templates for the two
load-bearing doc types (ADRs, runbooks) that show up across the rest of Phase 0A.

This is the first STOP-tier task — nothing builds without it.

## Files added

| File | Purpose |
|---|---|
| `AGENTS.md` | Vendor-neutral operating contract. Hard rules (V2 canonical, Conventional Commits, STOP/ARCH gates, tests with code, `memory.write()`-only, structured logging, no green-claim before green CI) and soft defaults. Picked up natively by tools following the emerging `AGENTS.md` convention. |
| `CONTRIBUTING.md` | Short human-facing entry point. Points at AGENTS.md, V2 spec, ADR + runbook directories. Documents commit conventions, branching (`feature/<task-id>-<short-slug>`), review gates, findings handling. |
| `commitlint.config.js` | Conventional Commits 1.0.0 + the V2 spec's allowed types/scopes. Consumed by T0.A2 (pre-commit hook) and T0.A4 (CI). `header-max-length: 100`. |
| `docs/adr/0000-template.md` | Michael Nygard ADR template — Status / Context / Decision / Consequences / Alternatives / References. The shape of every architectural decision record from now on. |
| `docs/runbooks/0000-template.md` | Symptom → Diagnosis → Fix → Root cause → Prevention template. Status + Last-verified dating. The shape of every known-failure-mode entry. |

## Allowed types and scopes (frozen by this PR)

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`
**Scopes:** `memory`, `runtime`, `ui`, `agent`, `prompt`, `infra`, `ci`, `docs`, `migration`, `repo`, `auth`, `obs`, `ops`

These come straight from the V2 spec §"Conventional Commits — Enforced." They are
the contract — any change requires a deliberate spec amendment.

## Spec deviations

None. The deliverables list in V2 §T0.A1 is met exactly: AGENTS.md (vendor-neutral),
Conventional Commits config, ADR template, runbook template. CONTRIBUTING.md is
added on top as the human-facing pointer file (V2 doesn't forbid; it's standard
GitHub repo hygiene and complements rather than duplicates AGENTS.md).

## What this unlocks

- **T0.A2 (Pre-commit hooks)** consumes `commitlint.config.js` directly. Without
  this, A2 has nothing to enforce.
- **T0.A3 (Test harness)** lands code; that code lands under the
  "tests come with the code" hard rule from `AGENTS.md`.
- **T0.A4 (CI pipeline)** runs commitlint in CI using this same config. Without
  this, A4 can't gate anything.
- **Every subsequent ADR (T0.A5 storage decision, T0.A12 container build, T2.x
  agent shape decisions)** uses `docs/adr/0000-template.md`.
- **Every subsequent runbook (T0.A10 backup-restore, T0.A11 cost kill-switch,
  T1.x deploy procedures)** uses `docs/runbooks/0000-template.md`.

Phase 0A pacing note: this is task 1 of 15 infra tasks before any product-visible
change ships. The contract laid down here is what makes the next 14 tasks legible
to reviewers and to future agents picking up cold.

## STOP gate

Standing by for Maxwell QA. After approval + merge, T0.A2 starts immediately
(pre-commit hooks consume this config).
