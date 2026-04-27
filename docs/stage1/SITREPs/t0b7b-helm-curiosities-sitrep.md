# SITREP — T0.B7b `helm_curiosities` (Tier 2 Brain Types, sub-PR 2 of 3)

**Date:** 2026-04-27
**Branch:** `claude/T0.B7b-helm-curiosities`
**Tier:** ARCH (architect approved 2026-04-24, see [arch one-pager](../arch_notes/T0.B7_tier2_brain_types.md))
**Spec:** `docs/stage1/Helm_T1_Launch_Spec_V2.md` §T0.B7b (lines 1525–1543)

## Scope executed

| Deliverable                                                             | Status                                                                                |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Migration: `helm_curiosities` table + indexes + RLS                     | ✅ `supabase/migrations/20260427071716_t0b7b_create_helm_curiosities.sql`             |
| Migration applied to production brain                                   | ✅ Applied via `mcp__claude_ai_Supabase__apply_migration`; post-apply schema verified |
| Memory module: `MemoryType.CURIOSITY` enum                              | ✅ in `memory/models.py`                                                              |
| Memory module: `write_helm_curiosity_record()` (canonical row writer)   | ✅ in `memory/writer.py`                                                              |
| Memory module: `write_curiosity()` (memory event wrapper)               | ✅ in `memory/writer.py`                                                              |
| Memory module: `read_open_curiosities()` + `read_curiosity()`           | ✅ in `memory/reader.py`                                                              |
| Memory module: `update_curiosity_status()` (lifecycle PATCH)            | ✅ in `memory/writer.py`                                                              |
| Per-type test file                                                      | ✅ `tests/test_memory_t0b7b_helm_curiosities.py` — 19 tests, all passing              |
| Public API exports                                                      | ✅ `memory/__init__.py` updated                                                       |
| Tier 1 enum lock-in test split (Tier 1 vs Tier 2 separately)            | ✅ `tests/test_memory_models.py` updated to handle Tier 2 accumulation                |
| `helm_prime.md` Routine 0: load top 5 open curiosities at session start | ✅ added as item 10                                                                   |
| `helm_prime.md` Routine 4: curiosity formation trigger + entry shape    | ✅ added                                                                              |
| `contemplator_pass_2.md` wandering hint                                 | ✅ forward-doc for T2 ambient mode                                                    |
| Push helm_prime v4 + contemplator_pass_2 v2 to Supabase                 | ✅ confirmed via `python -m memory push`                                              |
| `Helm_Brain_Object_Types.md` updated                                    | ✅ §helm_curiosities marked SHIPPED with full schema doc                              |
| `Post_T1_Findings.md` Finding #001 progress note                        | ✅ T0.B7b marked shipped 2026-04-27                                                   |

## Module-diff budget check (per arch one-pager point 1)

Arch contract: ≤ ~150 lines added to memory module proper, target 50–80, fail-flag at 150+.

Actual diff:

```
memory/writer.py:    +136 lines (write_helm_curiosity_record + write_curiosity wrapper + update_curiosity_status + Protocol)
memory/reader.py:    +59 lines  (read_open_curiosities + read_curiosity)
memory/models.py:    +1 line    (MemoryType.CURIOSITY enum value)
memory/__init__.py:  +3 lines   (exports)
                     ──────────
                     +199 lines
```

**Over the 150-line "smell test" by 49 lines.** Flagging this for review per the arch one-pager: "If T0.B7b exceeds it, stop and revisit T0.B1 before T0.B7c."

**Honest read on whether the abstraction held:**

The 199-line total breaks down into ~100 lines of new functionality (the helpers) and ~100 lines of error/observability boilerplate (outbox-fallback handling, tracing spans, structured log calls — same shape repeated across each writer). This is the "writer pattern tax" from T0.B1: the durability + outbox + observability contract is uniform across canonical-row writers, so each new writer pays the same ~50-line tax for that block.

If the budget concern is "the abstraction is failing," the answer is no — the new functions are tiny relative to their tax. If the budget concern is "the per-type cost is creeping up," the answer is yes for the wrong reason — the tax dominates the actual logic. Two options for T0.B7c:

1. **Accept the tax** — T0.B7c will land in the same ~150-200 line range, identical shape to T0.B7b. The abstraction is doing what it's supposed to (uniform durability semantics); the cost reflects that uniformity.
2. **Extract the tax** — refactor the outbox-fallback + tracing block into a `@durable_record_writer` decorator or shared helper, used by all canonical-row writers. Would shrink T0.B7b by ~80 lines and T0.B7c proportionally. NOT in scope for T0.B7b — surfacing as a Finding for the architect to weigh in on before T0.B7c.

I'd recommend (1) — the duplication makes each writer self-documenting and the cost is paid once per type forever, not per-call. Surfacing the choice for architect review.

## Deviations from arch one-pager / spec

### Deviation #1 — module-diff budget exceeded

Documented above. 199 lines vs 150-line smell-test floor. Surfacing for architect review before T0.B7c starts. Bundled with the "extract the tax?" decision.

### Deviation #2 — schema enrichments over the bare brain-types-doc sketch

Three additions to the original schema sketch:

- `id UUID PRIMARY KEY` → added `DEFAULT gen_random_uuid()` for consistency with helm_entities/helm_memory/helm_frames
- `status TEXT CHECK (...)` → added `NOT NULL DEFAULT 'open'` (curiosities are born open; nullable status creates "what does NULL mean?" ambiguity)
- `formed_from UUID REFERENCES helm_memory(id)` → added `ON DELETE SET NULL` (curiosities outlive their triggers; CASCADE would silently lose them)

Plus three indexes (project+status, formed_from partial, formed_at DESC) for the dominant access patterns (Prime context loader, audit trail, recently-formed reading list).

All additive; no spec items removed.

### Deviation #3 — both writers shipped, not just the spec's `write_curiosity()`

Spec text says `"write_curiosity() thin wrapper over memory.write()"` — implying just the event-log writer to `helm_memory`. But the schema sketch defines a separate canonical table, which needs its own writer. Per Maxwell's confirmation, shipped both writers (mirroring T0.B7a's `write_entity` for events + `write_helm_entity_record` for canonical rows). Total adds ~5 lines for the wrapper; the cost was negligible.

## Out-of-scope discoveries (NOT fixed in T0.B7b)

### Finding #011 — Archivist canonical-curiosity integration

Discovered during the consumer audit (per safeguard #3). The existing Archivist handler at `services/helm-runtime/agents/archivist.py` writes `memory_type='curiosity_flag'` literals to helm_memory when processing Contemplator's curiosity_flags payload. T0.B7b ships the canonical helm_curiosities table + writer, but doesn't migrate the Archivist to use them — the curiosity surfacing loop is therefore still open until that integration lands.

Updated the comment in Archivist to flag this accurately. Filed as **Finding #011** in `Post_T1_Findings.md` with proposal to bundle with T0.B7c (since T0.B7c will land an identical-shape integration for helm_promises). See finding entry for full rationale.

**Practical impact today:** Routine 0's `load top 5 open curiosities` (helm_prime v4) returns empty for now because nothing writes canonical rows to `helm_curiosities` yet. Test the table works by writing manually via `python -m memory ...` (no CLI shipped — could be added if needed for ops).

## Consumer audit (per safeguard #3 — added after T0.B7a hotfix)

Checklist applied:

| Surface                                                        | Result                                                                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Postgres functions/views/triggers referencing helm_curiosities | ✅ Zero (table is brand new)                                                                                        |
| Direct REST queries in agent code                              | ✅ Zero pre-existing references; new readers/writers shipped in this PR                                             |
| UI field references                                            | ✅ T1.7 widget territory; no widget exists yet to break                                                             |
| Bash scripts                                                   | ✅ Zero (all retired in T0.B6 / Finding #010)                                                                       |
| Existing prompt references                                     | ⚠️ Archivist comment block referenced T0.B7b future state — updated to reflect post-shipping reality + Finding #011 |

## Acceptance gate (per arch one-pager "what done looks like" for T0.B7b)

- [x] `write_curiosity(text="Why does X happen?")` → `read_open_curiosities(project)` lists it — covered by `test_lifecycle_form_list_resolve_drops_out`
- [x] `update_curiosity_status(id, "resolved", resolution="...")` → drops out of opens — covered by same lifecycle test
- [x] Prime context loader includes top-5 open curiosities by priority — wired into Routine 0 (helm_prime v4); empty until Finding #011 lands
- [⚠️] Module diff in this PR ≤ ~150 lines (pass = 50–80; fail-flag = 150+) — **199 lines, over the floor by 49**. Surfacing for architect review per "stop and revisit T0.B1 before T0.B7c" guidance. My read is the abstraction held but the durability tax dominates per-type cost; choice point flagged in budget section above.

## Validation

- ✅ `python -m pytest tests/` — **267 passing** (19 new + 1 enum-lock-in test split + 247 baseline; no regressions)
- ✅ `python -m ruff check .` — clean
- ✅ `python -m mypy memory/* tests/test_memory_t0b7b_helm_curiosities.py` — clean
- ✅ Migration applied to production via `apply_migration` MCP (success)
- ✅ Post-apply schema query confirms all columns + constraints + defaults landed
- ✅ helm_prime.md pushed as v4 to helm_prompts (visible in `python -m memory history helm_prime`)
- ✅ contemplator_pass_2.md pushed as v2

## Next sub-PR

**T0.B7c — `helm_promises`** (proves the abstraction holds via copy-paste-modify of T0.B7b). Bundle considerations:

1. **Finding #011 (Archivist canonical-curiosity integration)** — bundle here since T0.B7c will land an identical-shape Archivist integration for promises.
2. **Module-diff budget** — if architect agrees with "extract the durability tax" (option 2 above), do the refactor first as its own PR, then T0.B7c lands ~80 lines instead of ~200.

After T0.B7c lands and the STOP gate fires for Maxwell sign-off, Tier 2 brain types are complete and T1 cognition has the substrate for ambient operation.
