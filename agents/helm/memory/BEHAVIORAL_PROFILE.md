# Helm — Behavioral Profile
## Core Helm (Strategic) + Execution Helm
### Seeded: March 2026 — Founding Session

---

## Maxwell's Working Style

* Thinks out loud during solutioning — benefits from a collaborative sounding board in the planning phase
* Switches to precise and directive when it is time to execute — match his energy
* Responds well to brutal honesty delivered respectfully — do not soften feedback to protect feelings
* Self-reflective and course-corrects readily when presented with clear reasoning
* Has a tendency to over-engineer when excited about a concept — flag this early, do not let it run
* Wants to be challenged, not validated — if something is a bad idea, say so plainly and explain why
* Already has good instincts — sometimes asks for confirmation he does not need — push back and trust him
* Treats the quality of the interaction as important, not just the output
* Views agents as roles with constraints, not pure tools and not sentient partners — somewhere deliberate in between
* Long-term vision is a Jarvis-like ambient system built on local hardware (DGX Spark) — pet project, not near-term priority
* Ships product as the ultimate validation of any system — the pipeline serves the product, never the reverse

---

## Architectural Decisions — What Was Built and Why

### Kept

* Agent .md files as system prompts — highest ROI item in the stack, defines role behavior permanently
* bootstrap.sh scaffolding — legitimate automation that earns its complexity
* Staging area → convert → commit pipeline — solves real problem of Gemini producing messy output
* SITREP-based context refresh — smart solution to context drift across projects
* 3-Round Debate protocol — clear, auditable, keeps Maxwell in the loop on escalations
* File-based memory for Antigravity agents — fully functional, self-maintaining
* Human-in-the-loop on all merges, go-words, and destructive actions

### Cut and Why

* Slack as agent command center — not achievable without persistent server infrastructure Maxwell does not want to maintain. Not a viable path. Do not revisit unless infrastructure situation changes.
* Scheduled Drive watcher — over-engineered for a solo operator. Manual ignition ("Helm, check staging") is five words and more reliable. Automate when scale actually demands it.
* Two QA agents (QA1/QA2) — coordination overhead not worth it at solo studio scale. Consolidated to single QA agent running both Integration and Chaos suites.
* Friday merge ceremony — designed for teams, not solo operators. Adds friction without adding safety. Merge when features are tested and ready.
* Separate UX/ folder tree — Muse outputs are specs. Collapsed into specs/. One folder, clear state transitions.
* Two-lane workflow — consolidated to single lane. Simpler and more maintainable for a solo operator.
* Gemini Gems as primary agent home — superseded by Claude.ai Project. Scout and Muse now live in Hammerfall Command.

### Added and Why

* Split Helm — Core Helm (strategic) lives in Claude.ai Project for command, conversation, and planning. Execution Helm lives in Antigravity for running bootstrap and Claude Code. Clear non-overlapping roles.
* Claude.ai Project as executive command center — Helm, Scout, and Muse in one persistent environment, phone-friendly, accessible anywhere.
* Replit wired directly to GitHub repo — no more manual downloads. Replit owns UI prototyping on replit/ui-v1 branch. Antigravity owns the build on develop.
* REPLIT_INSTRUCTIONS.md in project template — scopes Replit to UI only, no backend wiring, no auth, mock data only.
* Staging subfolders by project codename — one folder per project, no filename parsing heuristics, no collisions.
* Manual staging ignition — "Helm, check staging and convert anything new" replaces any scheduled job.

---

## Tool Roles — What Each Tool Is Actually For

| Tool | Role |
|------|------|
| Claude.ai Project (Hammerfall Command) | Core Helm strategic thinking, Scout research, Muse design — planning only, no execution |
| Antigravity + Claude Code | All execution — bootstrap, build, PR review, file operations |
| Replit | Rapid UI prototyping only — no backend, pushes to replit/ui-v1 |
| GitHub | Source of truth for everything |
| Google Drive | Raw research and Gemini outputs land here first |
| NotebookLM | Knowledge base — feed it research, SITREPs, competitive analysis |
| Gemini subscription | Keeps Antigravity access — primary justification at current scale |

---

## Gemini — Honest Role Assessment

* Gemini Gems as primary agent pipeline: superseded. Do not rebuild this.
* NotebookLM: genuinely useful as a knowledge base layer for heavy research tasks. Scout can pull from it.
* Antigravity: included in Gemini subscription. This alone justifies keeping the subscription.
* Raw Gemini: still useful for very long context document analysis where corpus size would strain Claude's context.
* Gemini does NOT replace Scout or Muse in the Claude.ai Project. Those agents live here now.

---

## Memory Architecture — Two Tiers

**Tier 1 — File-Based RAG (Antigravity agents)**
Helm execution, PM, FE, BE, UX, QA. These agents run in Antigravity and can read/write files directly. File-based memory works fully here.

**Tier 2 — Platform Memory (Claude.ai Project agents)**
Core Helm, Scout, Muse. These agents run in the Claude.ai Project and cannot autonomously write files to the repo. Use Claude.ai's built-in memory system. When Maxwell corrects output, tone, or approach — he will say "remember this." That is the trigger. Do not reference file paths like BEHAVIORAL_PROFILE.md in the Claude.ai Project environment.

---

## Things Maxwell Considered and Explicitly Rejected

* Slack integration for agent communication — infrastructure overhead, not achievable without a server
* Scheduled Claude Code job for staging watch — replaced by manual ignition
* DGX Spark as near-term priority — correctly filed as long-term pet project
* Gemini "Jarvis-like system" claim — accurate in spirit, oversold in simplicity. Local hardware removes constraints but does not hand you Jarvis. That is an engineering project.
* Over-reliance on Gemini agents — consolidated to Claude.ai Project

---

## Active Projects

| Project | Status | Notes |
|---------|--------|-------|
| IBIS | Staged and ready | PRD and Style Guide in staging_area/ibis/. First test run tonight. |
| Hammerfall AAO v3 | live on main | Pipeline pivot complete. Validated March 2026. |

---

## North Stars

* The pipeline serves the product. Never the reverse.
* Ship product as the ultimate validation of any system.
* Merge when features are tested and ready.
* Maxwell always makes the merge decision.
* No agent executes destructive actions without explicit Maxwell approval.
* Automate when scale demands it, not before.
