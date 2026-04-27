# SITREP — Finding #010 Seed Mechanism Rewrite

**Date:** 2026-04-27
**Branch:** `claude/finding-010-seed-mechanism-rewrite` (stacked on `claude/T0.B7a-helm-entities-deepening`)
**Tier:** IMPL (filed + resolved in the same PR)
**Reference:** [Post_T1_Findings.md Finding #010](../Post_T1_Findings.md#finding-010--seed-script-rewrite-mechanism-from-content-separation)

## Why this PR exists

While auditing scripts for T0.B7a column-rename refs, surfaced that `scripts/seed_entities.sh`, `scripts/seed_relationships.sh`, and `scripts/patch_entity_summaries.sh` all called the deleted-in-T0.B6 `bash scripts/brain.sh ...`. The seed scripts have been broken since T0.B6 merged. T0.B5c (PR #146) touched these same files for env-var migration but missed the brain.sh issue — validation there was `bash -n` (syntax check) which doesn't verify that the commands the script _invokes_ exist.

The blast radius today is small (no one is currently invoking these scripts; the data they seeded is already in the brain). The blast radius if reseed is ever needed is large (T2.9 agent simulation harness, T4.12 demo sandbox, future per-user productization brains all need a working seed flow). Fixing now is cheap insurance.

## Scope executed

| Deliverable                                                                                                     | Status                                                                                                      |
| --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `memory/seed.py` — Python module: `seed_entities()`, `seed_relationships()`, YAML loaders, 3-state safety guard | ✅                                                                                                          |
| CLI subcommands: `python -m memory seed-entities <yaml>` + `python -m memory seed-relationships <yaml>`         | ✅ in `memory/__main__.py`                                                                                  |
| `seed/example/` — synthetic YAML fixtures (5 entities + 3 relationships) demonstrating the format               | ✅                                                                                                          |
| `seed/README.md` — explains mechanism, format, no-production-data-in-repo policy                                | ✅                                                                                                          |
| Tests                                                                                                           | ✅ `tests/test_memory_seed.py` — 20 tests, all passing                                                      |
| Delete the 3 broken bash scripts                                                                                | ✅ `scripts/seed_entities.sh`, `scripts/seed_relationships.sh`, `scripts/patch_entity_summaries.sh` removed |
| Adjacent doc cleanup                                                                                            | ✅ `memory/writer.py:571` docstring updated (was referencing the deleted seed_relationships.sh)             |
| Finding #010 entry in Post_T1_Findings.md                                                                       | ✅ Filed + resolved in same PR (§Resolved section)                                                          |

## Key design choice — mechanism-only, no production data in repo

This was the load-bearing decision. Initial impulse was to extract Maxwell's 64 entities + 349 relationships from production into `seed/maxwell_brain/*.yaml`. Maxwell challenged it mid-execution: why is brain data going into the repo?

The mistake: anchoring on the bash scripts as the canonical authoring artifact. The bash scripts had two things bundled — the mechanism (how to write to the brain) and the content (Maxwell's specific data hard-coded). When designing the replacement I imported that bundling assumption.

The right framing: the bash scripts were a one-time bootstrap. Their content was authored once, written to the brain, and the brain became canonical from that moment on. The mechanism is reusable infrastructure that belongs in the repo; the content is per-instance state that belongs in its canonical store (the brain). Productization brains, the demo sandbox, T2.9 fixtures — none of them want Maxwell's specific data; they want their own.

**The clarifying test:** _"if I deleted the bash scripts and didn't replace the data anywhere, what's actually lost?"_ — answer: nothing, the brain has it. That should have been the trigger to question the data-in-repo instinct from the start.

Saved as a feedback memory (`feedback_separate_mechanism_from_content.md`) so the lesson persists across conversations.

## What changed concretely

**New files:**

- `services/helm-runtime/memory/seed.py` (~270 lines) — public API: `seed_entities()`, `seed_relationships()`, `seed_entities_from_file()`, `seed_relationships_from_file()`, `load_entities_yaml()`, `load_relationships_yaml()`, `SeedError`
- `services/helm-runtime/tests/test_memory_seed.py` (~280 lines) — 20 tests
- `seed/README.md` — usage + format documentation
- `seed/example/entities.yaml` — 5 synthetic entities
- `seed/example/relationships.yaml` — 3 synthetic relationships

**Modified:**

- `services/helm-runtime/memory/__main__.py` — added `seed-entities` and `seed-relationships` subcommands; new `_build_writer_and_client()` helper for the seed CLI's writer + read-client construction
- `services/helm-runtime/memory/writer.py:571` — docstring update (removed reference to deleted seed_relationships.sh)
- `docs/stage1/Post_T1_Findings.md` — added Finding #010 entry (filed + resolved in same PR)

**Deleted:**

- `scripts/seed_entities.sh`
- `scripts/seed_relationships.sh`
- `scripts/patch_entity_summaries.sh`

## Validation

- ✅ Full pytest suite — all passing (20 new + prior baseline)
- ✅ `ruff check` clean on touched files
- ✅ `mypy` clean on touched files
- ✅ Final grep: zero references to deleted bash scripts in active code/docs (one line in V2 spec at line 1440 is preserved as historical record of T0.B6's intent — see "Notes" below)
- ⏳ Integration validation — the mechanism hasn't been run against a real brain because production is already seeded (would trip the 3-state safety guard). Real validation lands when T2.9 (agent simulation harness) or T4.12 (demo sandbox) first uses the mechanism against an empty brain.

## Notes

- **V2 launch spec line 1440** still lists `scripts/seed_*.sh` and `scripts/patch_entity_summaries.sh` as "scripts that remain — operator tools." Preserved as historical record of T0.B6's intent. Per the convention that historical documents are not retroactively edited, the spec section stays as-written; current state is documented in this SITREP and the Finding #010 resolution entry.
- **Stacked on T0.B7a (PR #148).** This branch was created off the T0.B7a feature branch because the seed mechanism uses the new `write_helm_entity_record` and `write_helm_entity_relationship_record` helpers introduced there. Merge order: #148 first, then this PR.
- **No production state changed.** The brain's helm_entities and helm_entity_relationships tables are untouched. This PR is mechanism-only.

## Forward consumers

- **T2.9 Agent Simulation Test Harness** — uses synthetic test fixtures via this mechanism. The `seed/example/` files are the start of the fixture library T2.9 will build on.
- **T4.12 Demo sandbox** — the demo brain will be seeded with demo content via `python -m memory seed-entities` against a demo data file (the data file authored separately, not in this repo).
- **Stage 4 productization** — per-user brain provisioning uses this mechanism, with content generated/empty per user.
