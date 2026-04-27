# Seed mechanism

Helm's brain seeding infrastructure. Replaces the bash seed scripts (`scripts/seed_*.sh`, `scripts/patch_entity_summaries.sh`) that were retired alongside `brain.sh` in T0.B6. See [Finding #010](../docs/stage1/Post_T1_Findings.md#finding-010--seed-script-rewrite-mechanism-from-content-separation) for the full story.

---

## What's here

```
seed/
├── README.md         (this file)
└── example/
    ├── entities.yaml          (5 synthetic entities — format demo + test fixture)
    └── relationships.yaml     (3 synthetic relationships)
```

**No production brain content lives in this repo.** The Supabase brain is the canonical store of every Helm instance's entities and relationships. Maxwell's brain content lives in his brain. The demo sandbox brain (T4.12) will live in the demo brain. Per-user brains in productization will live in their own brains. None of those instances duplicate state into the repo.

The example files exist purely to (a) show the YAML format the seed mechanism consumes and (b) serve as the test fixture for `tests/test_memory_seed.py`.

---

## How to use

The seed mechanism lives in [`services/helm-runtime/memory/seed.py`](../services/helm-runtime/memory/seed.py) and is exposed via two CLI subcommands:

```bash
cd services/helm-runtime

# Seed entities first — establishes name → UUID map in the brain
python -m memory seed-entities <path-to-your-entities.yaml>

# Then seed relationships — references entities by name, resolves to UUIDs
# by querying helm_entities at run time
python -m memory seed-relationships <path-to-your-relationships.yaml>
```

Both commands honor the `SUPABASE_BRAIN_URL` + `SUPABASE_BRAIN_SERVICE_KEY` env vars (or the `HELM_MEMORY_*` overrides). See [`docs/onboarding.md`](../docs/onboarding.md) for env setup.

---

## Safety contract

The seed mechanism preserves the 3-state safety guard from the bash predecessor:

| Current state                        | Behavior                                                     |
| ------------------------------------ | ------------------------------------------------------------ |
| Table is empty (clean slate)         | Proceed — write all entries                                  |
| Table has exactly the expected count | Already seeded — return without writing (idempotent re-runs) |
| Table has 1 row up to (expected − 1) | Raise `SeedError` — partial state, manual recovery needed    |

The "expected count" is `len(entities)` for the entities file or `len(relationships)` for the relationships file. So accidentally re-running the same seed file produces no duplicates.

---

## File format

### `entities.yaml`

```yaml
entities:
  - entity_type: person # required — must satisfy CHECK enum
    name: Alice # required — used as the resolution key for relationships
    aliases: [Ali, A] # optional — array of alternate names
    attributes: { ... } # optional — JSONB blob for type-specific fields
    summary: '...' # optional — one-sentence description
    salience_decay: 1.0 # optional — defaults to 1.0 in the schema
```

**Allowed `entity_type` values** (per the `helm_entities` CHECK constraint added in T0.B7a): `person`, `project`, `concept`, `place`, `organization`, `tool`, `event`, `pet`.

### `relationships.yaml`

```yaml
relationships:
  - from: Alice # required — entity NAME (not UUID); resolved at run time
    to: Bob # required — entity NAME
    relationship: friend # required — free-text label
    notes: '...' # optional — context like "biological", "step-relationship"
    confidence: 0.9 # optional — 0.0-1.0 score; NULL means no score
    active: true # optional — defaults true; false = retired (audit-trail)
```

**Bidirectionality is the author's responsibility.** Some relationships are symmetric (`Alice ↔ Bob` `friend`); others are asymmetric (`Alice → Bob` `parent`, `Bob → Alice` `child`). Author each direction explicitly when both are needed. The seed mechanism does no auto-flipping.

---

## Where this fits in the broader story

- **T0.B6 (PR #144)** retired `brain.sh`. Seed scripts that depended on it were left functionally broken.
- **T0.B7a (PR #148)** deepened the `helm_entities` schema (renames + new columns + CHECK constraint).
- **Finding #010 (this PR)** retired the broken bash scripts entirely, replacing them with this Python mechanism that goes through the memory module's `write_helm_entity_record` / `write_helm_entity_relationship_record` helpers (inheriting outbox-fallback, observability, CHECK enforcement automatically).
- **Forward consumers:**
  - **T2.9** Agent Simulation Test Harness — uses synthetic test fixtures via this mechanism (the `example/` files are the start of that)
  - **T4.12** Demo sandbox — the demo brain will be seeded with demo content via this mechanism (demo content authored separately, not in this repo)
  - **Stage 4 productization** — per-user brain provisioning uses this mechanism, with content generated/empty per user
