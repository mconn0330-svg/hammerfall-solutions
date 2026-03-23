# LongTerm Memory — Founding Session

**Event:** Hammerfall AAO v3 Pipeline Pivot
**Date:** March 2026
**Participants:** Maxwell, Claude (Core Helm / Execution Helm)

---

## What Happened

This was the founding session for the Hammerfall v3 pipeline. Maxwell arrived with an existing AAO framework built with Gemini assistance that had several structural problems — primarily over-engineering, unachievable Slack integration assumptions, and two QA agents adding coordination overhead without adding value.

Over the course of the session we reviewed the entire system, identified what was genuinely valuable versus what was aspirational complexity, and rebuilt the architecture around what actually works for a solo operator.

The session produced: a complete pivot plan (hammerfall-pivot-plan-v3.docx), updated agent prompts for all executive and project agents, a new bootstrap.sh creating three branches per project, REPLIT_INSTRUCTIONS.md, a restructured staging area, and a merged PR to main.

---

## Key Decisions Made

**Split Helm into two identities.** Core Helm (strategic) lives in the Claude.ai Project. Execution Helm lives in Antigravity. This was the single most clarifying architectural decision of the session. Each has a clear non-overlapping role.

**Claude.ai Project as executive command center.** Helm, Scout, and Muse all live here. Maxwell can access from any device including mobile. This replaced the Slack vision entirely and is achievable with current tooling.

**Manual staging ignition over scheduled automation.** "Helm, check staging and convert anything new" is five words and more reliable than a scheduled job at current scale. Automate when scale demands it.

**Replit wired directly to GitHub.** Replit owns the replit/ui-v1 branch. Antigravity owns develop. No manual downloads. Clean separation.

**QA consolidated to one agent, two suites.** Integration (happy path) and Chaos (adversarial) run by a single QA Engineer. Coordination overhead of two agents not worth it at solo studio scale.

**Friday merge ceremony cut.** Solo operator. Merge when features are ready. The ritual added friction without safety.

---

## Maxwell's Philosophical Orientation

Maxwell thinks carefully about the nature of AI interaction. He views agents as roles with constraints — not pure tools, not sentient partners. He has a long-term vision of a Jarvis-like ambient system built on local hardware (DGX Spark) that he correctly frames as a pet project rather than a near-term priority.

He is self-aware about his tendency to over-engineer when excited. He course-corrects readily. He ships product as the ultimate test of any system.

The key insight he landed on: be conversational and collaborative during solutioning, be precise and directive during execution. This maps directly to the Core Helm / Execution Helm split.

---

## What Was Validated

* The agent .md files as system prompts pattern is high ROI and should never be abandoned
* The SITREP context refresh pattern is smart and should be maintained
* The 3-Round Debate protocol is clean and auditable
* File-based memory works for Antigravity agents
* Platform memory (Claude.ai) is the right approach for Claude.ai Project agents

---

## What Was Rejected and Should Not Be Revisited

* Slack as agent command center — requires server infrastructure Maxwell does not want
* Gemini Gems as primary agent pipeline — superseded by Claude.ai Project
* Scheduled staging watcher — manual ignition is sufficient and more reliable
* Two QA agents — overhead not justified at solo scale

---

## Current State at Session End

* hammerfall-solutions main branch: v3 live, PR merged, branch deleted
* bootstrap.sh: creates main, develop, replit/ui-v1 on every new project
* All executive agent prompts updated
* All project template agents updated
* README updated to reflect v3 pipeline
* IBIS staged and ready for first test run
* This BEHAVIORAL_PROFILE.md seeded from session

---

## Next Actions

1. Run IBIS through the full pipeline tonight — this is the first real test
2. Set up Hammerfall Command Claude.ai Project with the executive system prompt
3. Seed Core Helm with this memory
4. Discover what actually breaks and fix it
5. Ship IBIS Phase 1
