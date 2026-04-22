# Speaker — Deprecated

**Status:** Archived 2026-04-22 as part of Lane C Phase 3.
**Original location:** `agents/helm/speaker/speaker.md`
**Final code removal:** PR #78 (`refactor(runtime): remove Speaker agent`)

## What Speaker was

Speaker was the routing and sensing layer between Maxwell and Helm Prime in the
Thor-era pipeline architecture. It owned three responsibilities:

1. **Cognitive isolation.** Trivial mechanical work resolved at Speaker (Qwen 8B at T1,
   Llama 3.1 8B on Thor MIG partition 2 at T3) so Helm Prime's reasoning context was
   never burned on routing decisions.
2. **Request classification.** Every incoming Maxwell turn was triaged: simple → answer
   at Speaker; complex → escalate to Helm Prime.
3. **Personality injection.** On the Helm Prime escalation path Speaker loaded
   `helm_personality` scores from Supabase and appended them to the Prime system
   prompt before the call.

The contract is preserved here verbatim because the design rationale around cognitive
isolation, ambient sensing, and escalation thresholds may inform future agent designs
even though Speaker itself is gone.

## Why Speaker was deprecated

The Ambient Turn (`docs/founding_docs/Helm_The_Ambient_Turn.md` §4) replaced the
pipeline framing — *Helm as a director routing to specialist agents* — with the
ambient framing — *Helm as a single intelligence (Prime) that owns user-facing voice,
supported by cognitive subsystems (Projectionist, Archivist, Contemplator) that
operate alongside, not in front of, Prime*.

Under that framing Speaker has no role:

- **Routing is gone.** There is no specialist tier behind Helm Prime to route to.
  Every Maxwell turn is a Helm Prime turn. Trivial requests are handled by Prime
  itself; the cost of always invoking Prime is acceptable in the ambient model.
- **Cognitive isolation moved.** Projectionist, Archivist, and Contemplator already
  run as isolated subsystems — they read frames and write memory in parallel, never
  in line with Prime's response loop.
- **Personality injection migrated.** PR #76 moved personality block loading directly
  into `agents/helm_prime.py`. Speaker no longer had a unique runtime responsibility
  after that.

What remained was a routing layer that always routed to the same destination — dead
weight, conceptually and operationally.

## Why archive instead of delete

Three reasons:

1. **Audit trail.** The contract documents architectural decisions (cognitive
   isolation, escalation thresholds, sensor ownership at T3) that other readers may
   want to trace. Outright deletion erases that history; the git log preserves it but
   is less discoverable than a file in the repo.
2. **Future Holoscan integration.** The T3 sensor-ownership design in this contract
   is the cleanest articulation of "what the sensing layer should own." If a sensing
   subsystem returns under a different name, this is the right reference point.
3. **The Ambient Turn is a pivot, not a repudiation.** Many of Speaker's design
   constraints (PD compliance under routing decisions, never-deceive on classification
   transparency, escalation conservatism) are still right. They will likely
   reappear in some form. Archiving keeps that thinking accessible.

## Reading the archived contract

Read `speaker.md` as a historical document. Specifically:

- Anything describing **what Speaker does at runtime** is obsolete — Speaker no longer
  exists as a runtime component.
- Anything describing **what Speaker should escalate vs. resolve locally** is obsolete —
  there is no escalation tier under Helm Prime anymore.
- Anything describing **cognitive isolation patterns, sensor ownership at T3, and PD
  compliance under routing decisions** is design heritage worth preserving for any
  future sensing or routing subsystem.

## Cross-references

- **Code removal:** PR #78 — runtime, config, model pulls, stress tests
- **Reference scrub:** Lane C Phase 3 sub-PR 3 (planned) — clears Speaker mentions from
  living docs (`hammerfall-config.md`, `agents/shared/tier_protocol.md`,
  agent contracts, `COMPANY_BEHAVIOR.md`) and adds historical-document banners to
  `docs/ba1-5/`, `docs/ba6-9/`, `docs/stage0/`, `docs/stage1/`
- **Architectural rationale:** `docs/founding_docs/Helm_The_Ambient_Turn.md` §4
- **Phase 3.1 SITREP:** `docs/stage1/SITREPs/lane-c-phase3-speaker-code-deletion-sitrep.md`
