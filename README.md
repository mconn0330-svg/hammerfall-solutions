# Hammerfall Solutions - Autonomous AI Organization (AAO)

**Status:** ACTIVE
**Primary Objective:** Autonomous software validation, design, and development via specialized AI agents operating under strict Human-In-The-Loop (HIL) oversight.

## 🏢 The Org Chart
This repository serves as the "Company Brain" for Hammerfall Solutions. It contains the operational directives and persistent memory for our executive AI team.

- **[Helm] (Technical Director):** Orchestrates project launches, manages infrastructure, and acts as the final gatekeeper for production code. (`/agents/helm`)
- **[Scout] (Product Strategist):** Validates market fit, defines JTBD (Jobs to Be Done), and establishes GTM strategy. (`/agents/scout`)
- **[Muse] (UX/UI Architect):** Translates strategy into high-fidelity technical blueprints and component logic. (`/agents/muse`)

## 📜 Global Directives
All agents operating within this organization or its sub-projects are bound by the global laws defined in:
👉 `management/COMPANY_BEHAVIOR.md`

## 🚀 How to Launch a Project

**Step 1 — Research & Design (Claude.ai Project — Hammerfall Command)**
Talk to Scout to validate the concept and produce a PRD. Talk to Muse to produce the Blueprint and Style Guide. They save outputs to Google Drive staging subfolders.

**Step 2 — Stage the Specs**
Say: `Helm, check staging and convert anything new.`
Helm reads Drive, converts docs to clean .md files, and commits them to `staging_area/[codename]/`.

**Step 3 — Launch (Claude.ai Project + Antigravity)**
Say: `Helm, go word for [codename].`
Helm confirms the plan. Then run in Antigravity:
```
bash ./bootstrap.sh [codename]
```
This scaffolds the repo, creates `main`, `develop`, and `replit/ui-v1` branches, injects specs, and generates the initial SITREP.

**Step 4 — UI Prototype (Replit)**
Connect Replit to the new repo on the `replit/ui-v1` branch. Tell the agent: `Read REPLIT_INSTRUCTIONS.md and specs/ready/ before building.`

**Step 5 — Full Build (Antigravity)**
Open the repo in Antigravity on the `develop` branch. Run Claude Code and say: `Build the project. Follow CLAUDE.md. Use the agent system.`

**Step 6 — Review & Merge**
Agents open a PR. You review. You merge. Always.

## 🧠 Memory Architecture
- **Claude.ai Project agents** (Helm strategic, Scout, Muse): use Claude.ai platform memory. Say "remember this" to retain preferences.
- **Antigravity agents** (Helm execution, PM, FE, BE, UX, QA): use file-based memory in each agent's `memory/` folder.

*Warning: Do not modify the `/agents` memory structures manually. Antigravity agents manage their own file-based RAG architecture.*
