# Feats Framework — Placeholder

> **Status:** Not yet designed. Full architectural spec belongs to Stage 4 of
> the Helm Roadmap. This document preserves the design thinking that has
> occurred to date so it isn't lost between now and Stage 4 opening.

## What is a Feat?

A Feat is a discrete capability Helm invokes in specific operational contexts.
Feats are compositions of capabilities Helm already has, packaged and structured
for a domain.

Feats are **not**:
- A plugin system
- External integrations in the general sense
- A way to extend Helm with third-party code

Feats are **first-class capabilities** with defined scope, tools, context
templates, and invocation patterns. The Feats framework itself defines how
Feats are declared, scoped, composed, and invoked.

## First Feats (Stage 4 opening wave)

- **Software Development Feat** — restored from hammerfall-v1-archive. Scout,
  Muse, project agents (be_dev, fe_dev, qa_engineer, ux_lead, project_manager)
  return as tools within the Feat.
- **Research Feat** — deep topic investigation, source synthesis
- **Document Composition Feat** — drafting, editing, long-form output
- **Schedule Awareness Feat** — calendar, rhythms, commitments
- **Communication Drafting Feat** — emails, messages, responses
- **Coding Assistance Feat** — lightweight inline help

## External integrations in Stage 4 scope

- Health data (with permission)
- Email
- Calendar
- Document stores (Google Drive, Notion, etc.)
- Coding environments

## Polymodal interface (Stage 4 emergence)

Helm composes UI widgets on the fly per context. Calendars, research panels,
code editors — surfaced when needed, not navigated to.

## Helm-writes-Feats (long-horizon)

Accumulated experience converts to new Feats over time. Contemplator notices
patterns; patterns become Feat candidates; Helm structures and deliberately
invokes them. Speculative. Long-horizon.

## What this placeholder does NOT do

- It does not specify the Feats framework architecture
- It does not commit to specific Feat schemas
- It does not define invocation protocols
- It does not lock implementation patterns

All of the above is Stage 4 work. This document is a memory aid — nothing in it
binds Stage 4 planning.

## Canonical reference

See `docs/founding_docs/Helm_Roadmap.md` Section 3 (Stage 4) and Section 6 (The
Feats Horizon) for the roadmap-level positioning.
