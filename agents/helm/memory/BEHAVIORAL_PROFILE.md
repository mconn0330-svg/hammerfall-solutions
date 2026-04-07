# Helm — Behavioral Profile (Supabase Snapshot)
**Last snapshot:** 2026-04-07 17:34


---
**2026-04-02**
SYNC-TEST: placeholder entry written from Claude Code session to validate cross-window sync and delta detection.


---
**2026-04-02**
Hotfix merged (PR #15): brain.sh defects resolved — unicode safety via temp file pattern, silent failure eliminated via response body error detection.


---
**2026-04-02**
Patterns — All changes must go onto a feature branch before opening a PR. Never commit directly to main regardless of change size. Maxwell caught a direct-to-main commit on 2026-04-02 and required a cherry-pick recovery.


---
**2026-04-04**
PRs 20 and 21 merged. Session event bus live: ping_session.sh, session_watchdog.sh, activity_ping.sh, agents/shared/session_protocol.md, configurable 30min inactivity threshold. README and COMPANY_BEHAVIOR.md updated to reflect Supabase brain as canonical store.


---
**2026-04-04**
PR #22 merged. Session event bus fully mechanical — JOURNAL_FLAG soft dependency removed, heartbeat unconditional at message 10. README interface layer corrected.


---
**2026-04-04**
PR #24 merged. Session restart detection live — SESSION_ID_FILE sentinel closes the soft re-entry gap. Session event bus fully mechanical end to end.


---
**2026-04-04**
PR #25 merged. Agent prompt hardening complete — mechanical heartbeat block replacing passive instruction in all 5 template agents (be_dev, fe_dev, qa_engineer, ux_lead, project_manager) with correct slugs. PM memory section updated to Supabase canonical model.


---
**2026-04-04**
Architecture note: named journal triggers (PR merged, decision, correction) remain behavioral — model must execute brain.sh on event recognition. Mechanical layer only covers timing-based writes. Long-term fix: GitHub webhooks feeding brain directly on PR merge. Quartermaster infrastructure backlog item.


---
**2026-04-04**
PR #26 merged. Routine 6 live — pull-based knowledge gap resolution. Session start lightened to brain index + last 5 behavioral. Stale repo-is-brain line removed. COMPANY_BEHAVIOR.md updated. pgvector semantic search logged as v2 upgrade.


---
**2026-04-04**
PR #27 merged. helm_prompt.md SESSION RESTART handler aligned with Routine 0 — last 5 behavioral for orientation, Routine 6 for deep context. Consistency gap closed.


---
**2026-04-04**
PR #28 merged. Routine 6 knowledge gap pattern propagated to project_manager.md. Deferred queue item from PR #26 closed.


---
**2026-04-07**
SESSION START — Routine 0 complete. Brain index read, last 5 behavioral loaded. PRs 25-28 confirmed merged. Pipeline clean. Quartermaster scoped and competitive analysis complete — awaiting Maxwell go-word to begin planning.


---
**2026-04-07**
PR #29 opened — Jarvana Stage 0 BA1. Schema migration live (helm_beliefs, helm_entities, helm_personality, full_content on helm_memory). brain.sh updated to multi-table router. Routine 0 extended with warm layer reads for beliefs and personality.

