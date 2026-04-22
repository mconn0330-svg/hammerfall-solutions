# Hammerfall Solutions

Hammerfall is building Helm — an ambient intelligence.

## What is Helm?

One mind. Many surfaces. Persistent across time. See
[founding_docs/Helm_The_Ambient_Turn.md](founding_docs/Helm_The_Ambient_Turn.md)
for the full vision.

## Where are we in building him?

See [founding_docs/Helm_Roadmap.md](founding_docs/Helm_Roadmap.md) for the path
from today to ambient JARVIS. We are currently in **Stage 1 — Core Runtime & UI**.

## Repository structure

- `founding_docs/` — canonical reference documents (vision + roadmap)
- `agents/helm/` — Helm's cognitive architecture (Prime prompt + subsystem contracts)
- `services/helm-runtime/` — the runtime service that hosts Helm
- `scripts/` — brain tools, seed data, utilities
- `supabase/migrations/` — database schema evolution
- `docs/` — historical design documents and stage records
- `docs/archive/` — deprecated subsystems preserved for reference

## Quick start

The runtime stack is run via `docker-compose up` from `services/helm-runtime/`.
See that directory's README and `config.yaml` for environment variables and
provider configuration.

## Related repositories

- [hammerfall-v1-archive](https://github.com/mconn0330-svg/hammerfall-v1-archive) —
  pre-refounding pipeline work, preserved for future Feat restoration

## Contributing

Currently a solo-plus-AI-collaborator operation. Contributions from outside
parties are not presently accepted.
