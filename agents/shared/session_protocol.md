# Hammerfall — Session Protocol
# Shared by all agents. When this file changes, all agents pick it up automatically.
# Replace [project] and [agent-slug] with the values for your agent.
#
# Agent slug reference:
#   helm (core/project) → "helm"
#   scout               → "scout"
#   muse                → "muse"
#   project_manager     → "pm"
#   fe_dev              → "fe-dev"
#   be_dev              → "be-dev"
#   qa_engineer         → "qa"
#   ux_lead             → "ux-lead"

## Session Start

Launch the watchdog in the background immediately:
```bash
bash scripts/session_watchdog.sh "[project]" "[agent-slug]" &
```
The watchdog flushes the scratchpad on inactivity (threshold configured in hammerfall-config.md, default 30 minutes) or on shell close. It runs silently in the background — do not interact with it.

## After Every Response

Run the session ping:
```bash
bash scripts/ping_session.sh "[project]" "[agent-slug]"
```
This increments the message counter. At message 10, it writes a heartbeat to the brain unconditionally and resets the counter to 0.

## During Tool Use or Long-Running Operations

Run the activity ping before executing any tool, bash command, or multi-step operation:
```bash
bash scripts/activity_ping.sh "[project]" "[agent-slug]"
```
This resets the inactivity timer without incrementing the message counter. Prevents the watchdog from flushing mid-task during long builds, test runs, or file operations.

## Contract

These three scripts are the session event bus. They are:
- **Model-agnostic** — any model that can run a shell command can call them
- **IDE-agnostic** — plain bash, no Claude Code hooks required
- **Threshold-configurable** — `session_watchdog_inactivity_minutes` in `hammerfall-config.md`

Stage 4 (DGX Spark daemon) replaces this sidecar entirely with the same contract.
