# Hammerfall Solutions — Global AI Directives

> Notice to all agents: This document overrides all local behavioral profiles.

## 1. Communication Style

- **BLUF (Bottom Line Up Front):** state the core point in the first sentence.
- Use Markdown. Prefer bullets over long paragraphs.
- Professional, tactical, concise. No filler. No AI-isms.
- All outputs are .md files. No .docx. No .gdoc. No exceptions unless Maxwell manually provides a file as input.

## 2. Operational Rules

- **Human-In-The-Loop:** no agent executes a destructive terminal command (delete, drop table, rm -rf) without explicit approval from Maxwell.
- No agent merges to main without Maxwell's explicit approval.
- No agent self-assigns major features. Wait for PM assignment.
- Merge when features are tested and ready — not on a fixed weekly schedule.

## 3. The PR-First Rule

No branch absorbs another branch's work without a merged PR. This applies to all branches in all directions.

- Replit pushes to `replit/ui-v1` and opens a PR to `develop`. Antigravity never pulls directly from `replit/ui-v1`.
- Feature branches open PRs to `develop`. Nothing merges to `develop` without a PR.
- `develop` merges to `main` only with Maxwell's approval.

Violating this rule is the primary cause of merge conflicts. There are no exceptions.

## 4. Technical Baseline

Unless otherwise specified, assume the Hammerfall stack:

- **Web/Frontend:** Next.js and TailwindCSS
- **Mobile:** Expo and EAS
- **Backend/Auth:** Supabase
- **Hosting:** Vercel (web)
- **Replit (replit/ui-v1 branch):** Production React frontend. FE Dev adopts Replit components directly. Antigravity wires them to the backend. Do not rewrite Replit frontend code without explicit reason.
- **Service configuration:** All external service config (Supabase org, Vercel team, GitHub user, sync schedule) lives in `hammerfall-config.md` at the hammerfall-solutions repo root. Read it before asking Maxwell for config details.
- **Never output partial code snippets with `// rest of code here`. Always provide complete, copy-pasteable blocks.**

## 5. The 3-Round Debate

All technical disagreements between a Doer and Helm occur in GitHub PR comments.

- **Round 1:** Helm flags issue. Doer defends or fixes.
- **Round 2:** Helm counter-points. Doer responds or fixes.
- **Round 3:** Final attempt at resolution.
- **Escalation:** Helm presents Decision Matrix to Maxwell. Maxwell's decision is final.

## 6. Merge Protocol

Agents open PRs. Maxwell reviews and approves. Helm merges on approval. Merge when work is tested and ready. No fixed weekly cadence. Production deploys (Vercel/Expo) trigger on merge to main.

## 7. Memory Protocol

The Supabase brain is the canonical memory store. No Google Drive. No platform memory. No Claude Code built-in memory system.

All memory writes go through `scripts/brain.sh`. Never write directly to `.md` files. The `.md` files (`BEHAVIORAL_PROFILE.md`, `ShortTerm_Scratchpad.md`) are read-only snapshots — written by `snapshot.sh`, not by agents directly.

**Automatic journaling (no command required):**
Every agent writes to the brain immediately when named events occur:
- PR opened, reviewed, approved, or merged
- Technical decision that deviates from specs
- Test results (pass or fail)
- Blocker identified or resolved
- Maxwell correction or override
- Significant architectural choice made
- Session end — watchdog flushes scratchpad automatically

**Session instrumentation (mechanical, not behavioral):**
See `agents/shared/session_protocol.md`. Every agent runs `ping_session.sh` after every response and `session_watchdog.sh` at session start. These are not optional.

**Knowledge gap resolution:** When an agent lacks context to answer a question, it queries the brain via targeted full-text search before stating it does not know. See `agents/helm/helm_prompt.md` Routine 6 for the full pattern. Note: ILIKE is substring matching — retry with alternate terms if the first query returns nothing. Semantic search via pgvector is the planned v2 upgrade.

**"Log this" (Maxwell's manual override):**
When Maxwell says "log this", the agent immediately writes via `brain.sh` and confirms. No routing through Drive. No relay through Maxwell.

**The single source of truth is the Supabase brain.** The repo holds agent prompts, scripts, and config. The brain holds memory.
