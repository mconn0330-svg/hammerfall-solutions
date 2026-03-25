# Hammerfall Solutions — Autonomous AI Organization (AAO)

**Status:** ACTIVE
**Architecture:** IDE-First · Repo-Brain · Project Helm Clone
**Primary Objective:** Autonomous software validation, design, and development via specialized AI agents operating under strict Human-In-The-Loop (HIL) oversight.

---

## The Org Chart

This repository is the Company Brain for Hammerfall Solutions. All operational directives, agent personas, and persistent memory live here as .md files committed to Git.

### Executive Team (Core — this repo)

- **Helm** — Technical Director & Chief of Staff. Orchestrates project launches, manages infrastructure, reviews PRs, runs scheduled syncs across all projects. (`agents/helm/`)
- **Scout** — Senior Product Strategist. Validates market fit, defines JTBD, produces PRDs. (`agents/scout/`)
- **Muse** — Lead UX/UI Architect. Translates PRDs into technical blueprints and component specs. (`agents/muse/`)

### Project Team (per project repo, created by bootstrap.sh)

- **Project Helm** — Chief of Staff scoped to a single project. Reviews PRs, consumes SITREPs, coordinates agents. Syncs upward to Core Helm on schedule.
- **PM, FE Dev, BE Dev, QA Engineer, UX Lead** — Doer agents managed by Project Helm.

---

## Interface Layer

| Surface | Role |
|---|---|
| IDE (Antigravity standing session) | Primary desktop interface. Full agent coordination. All file operations. |
| Claude Code — Desktop App | Secondary desktop interface. Same repo access. Helm persona from .md files. |
| Claude Code — Mobile App | Mobile interface. Full agent coordination confirmed in UAT. Same repo = same brain. |
| Claude.ai Project (Hammerfall Command) | Retained for ideation and high-level strategy only. Not used for memory or execution. |

---

## Global Directives

All agents operating within this organization or its sub-projects are bound by:
`management/COMPANY_BEHAVIOR.md`

---

## How to Launch a Project

**Step 1 — Ideation (IDE or Claude Code)**
Talk to Scout to validate the concept and produce a PRD. Talk to Muse to produce the Blueprint and Style Guide. They save outputs to `staging_area/[codename]/` in this repo and commit.

**Step 2 — Check Staging**
Say: `Helm, check staging.`
Helm scans `staging_area/` for new project subfolders, reads every .md file, and reports what is ready and what is missing.

**Step 3 — Launch**
Say: `Helm, go word for [codename].`
Helm confirms the plan. Then run:
```
bash ./bootstrap.sh [codename]
```
This scaffolds the project repo, clones Project Helm with memory files, creates `main`, `develop`, and `replit/ui-v1` branches, injects specs, creates `SITREPs/TASKS.md`, and updates `active-projects.md`.

**Step 4 — UI Prototype (Replit)**
Connect Replit to the new repo on the `replit/ui-v1` branch. Tell the agent: `Read REPLIT_INSTRUCTIONS.md and specs/ready/ before building.`

**Step 5 — Full Build (Antigravity)**
Open the repo in Antigravity on the `develop` branch. Run Claude Code and say: `Build the project. Follow CLAUDE.md. Use the agent system.`

**Step 6 — Review & Merge**
Agents open PRs. Maxwell reviews and approves. Helm merges. No branch absorbs another without a merged PR.

---

## Memory Architecture

**Core Principle:** The repo is the memory. All agent state lives in .md files committed to Git.

Each agent maintains:
- `memory/ShortTerm_Scratchpad.md` — active working memory, updated continuously, flushed at session end
- `memory/BEHAVIORAL_PROFILE.md` — permanent record of decisions, preferences, and patterns learned
- `memory/LongTerm/MEMORY_INDEX.md` — card catalog of all archived events
- `memory/LongTerm/[Date]_[Topic].md` — dense permanent archives, written once, never edited

**Automatic journaling:** Agents update their memory files during every session without being told. Maxwell can say "log this" to trigger an immediate write to BEHAVIORAL_PROFILE.md for significant decisions.

**Scheduled sync:** Core Helm reads `active-projects.md` and syncs Project Helm memories upward at 7 AM, 12 PM, and 6 PM daily. On-demand via "Helm, sync now."

---

## Project Helm

Every project bootstrapped by Helm gets a Project Helm instance — a scoped copy of the Helm agent living at `agents/helm/` in the project repo. Project Helm is chief of staff for the build team:

- Reviews every PR to `develop`
- Reads every SITREP the PM produces
- Coordinates FE, BE, QA, and UX Lead
- Flags `[SYNC-READY]` entries for Core Helm to detect on sync
- Escalates unresolved disputes to Maxwell directly

Project Helm does not replace Core Helm on strategic decisions. Maxwell communicates directly with both.

---

## Key Files

| File | Purpose |
|---|---|
| `management/COMPANY_BEHAVIOR.md` | Global directives — overrides all local profiles |
| `agents/helm/helm_prompt.md` | Core Helm persona and routines |
| `agents/scout/scout_prompt.md` | Scout persona and handoff protocol |
| `agents/muse/muse_prompt.md` | Muse persona and blueprint structure |
| `active-projects.md` | Manifest of all live project repos |
| `bootstrap.sh` | Project scaffolder — creates repo, clones Project Helm |
| `scripts/sync_projects.sh` | Core Helm sync — reads project memories |
| `staging_area/` | Specs staged here before bootstrap |
| `project_structure_template/` | Master template copied by bootstrap.sh |

---

*Hammerfall Solutions · IDE-First Architecture · March 2026*
