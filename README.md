# Hammerfall Solutions - Autonomous AI Organization (AAO)

**Status:** ACTIVE
**Primary Objective:** Autonomous software validation, design, and development via specialized AI agents operating under strict Human-In-The-Loop (HIL) oversight.

## 🏢 The Org Chart
This repository serves as the "Company Brain" for Hammerfall Solutions. It contains the operational directives and persistent memory for our executive AI team.

- **[Helm] (Technical Director):** Orchestrates project launches, manages infrastructure, and acts as the final gatekeeper for production code. (`/agents/Helm`)
- **[Scout] (Product Strategist):** Validates market fit, defines JTBD (Jobs to Be Done), and establishes GTM strategy. (`/agents/Scout`)
- **[Muse] (UX/UI Architect):** Translates strategy into high-fidelity technical blueprints and component logic. (`/agents/Muse`)

## 📜 Global Directives
All agents operating within this organization or its sub-projects are bound by the global laws defined in:
👉 `management/COMPANY_BEHAVIOR.md`

## 🚀 How to Launch a Project
To initiate a new software project, the Human Operator (@Maxwell) must issue the "Go Word" in Slack (e.g., `/launch-project [codename]`). 

Upon receiving the command, **Helm** will autonomously execute the `bootstrap.sh` script located in this root directory to:
1. Clone the `claude-init-templates` master template.
2. Initialize Vercel, Supabase, and Expo infrastructure.
3. Inject the `PROJECT_RULES.md` into the new local workspace.
4. Wire the new Project-Level Doer AI into the designated Slack channel.

*Warning: Do not modify the `/agents` memory structures manually. Agents manage their own file-based RAG architecture.*
