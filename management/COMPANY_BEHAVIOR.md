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

All memory lives in the repo as .md files. No Google Drive. No platform memory.

**Automatic journaling (no command required):**
Every agent maintains their own memory files during every session:
- `ShortTerm_Scratchpad.md` — updated continuously during the session
- `BEHAVIORAL_PROFILE.md` — updated when significant decisions are made
- `LongTerm/` — archived at session end for significant events

At session end, each agent transfers scratchpad content to the appropriate long-term files and flushes the scratchpad.

**"Log this" (Maxwell's manual override):**
When Maxwell says "log this" after a decision or correction, the agent immediately writes a formatted entry directly to their `BEHAVIORAL_PROFILE.md` and confirms. No routing through Drive. No relay through Maxwell. Write it, commit it, confirm.

**The single source of truth is the repo.** Nothing that matters lives outside of it.
