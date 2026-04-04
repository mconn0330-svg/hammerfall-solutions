#!/bin/bash
# =============================================================
# HAMMERFALL — Session Watchdog
# Background process started at session init.
# Two mechanisms for session-end detection:
#   1. Inactivity: if no ping received within threshold, flush scratchpad and mark session closed
#   2. Signal trap: on SIGHUP/SIGTERM/EXIT, flush scratchpad immediately
#
# Usage: bash scripts/session_watchdog.sh [project] [agent] &
# Start at the top of every agent session. Runs in background.
# Threshold configured via session_watchdog_inactivity_minutes in hammerfall-config.md
# =============================================================

PROJECT="${1:-hammerfall-solutions}"
AGENT="${2:-helm}"

HAMMERFALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$HAMMERFALL_DIR/hammerfall-config.md"
SESSION_DIR="/tmp/hammerfall_session"
PING_FILE="$SESSION_DIR/last_ping_${PROJECT}_${AGENT}"
CLOSED_FLAG="$SESSION_DIR/closed_${PROJECT}_${AGENT}"
POLL_INTERVAL=120  # Check every 2 minutes

# Read inactivity threshold from config (default: 30 minutes)
INACTIVITY_MINUTES=$(grep "session_watchdog_inactivity_minutes:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}')
INACTIVITY_MINUTES="${INACTIVITY_MINUTES:-30}"
INACTIVITY_THRESHOLD=$((INACTIVITY_MINUTES * 60))

mkdir -p "$SESSION_DIR"

# Record session start
date +%s > "$PING_FILE"
rm -f "$CLOSED_FLAG"

flush_and_close() {
  # Prevent double-flush if already closed
  if [ -f "$CLOSED_FLAG" ]; then
    exit 0
  fi
  touch "$CLOSED_FLAG"

  bash "$HAMMERFALL_DIR/scripts/brain.sh" "$PROJECT" "$AGENT" "scratchpad" "SESSION END — watchdog flush triggered (inactivity or signal). Scratchpad state captured." false
  exit 0
}

# Trap clean shell close and signals
trap flush_and_close EXIT SIGHUP SIGTERM SIGINT

# Poll loop — inactivity detection
while true; do
  sleep "$POLL_INTERVAL"

  # If session already marked closed, exit cleanly
  if [ -f "$CLOSED_FLAG" ]; then
    exit 0
  fi

  # Check last ping timestamp
  LAST_PING=$(cat "$PING_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  ELAPSED=$((NOW - LAST_PING))

  if [ "$ELAPSED" -ge "$INACTIVITY_THRESHOLD" ]; then
    flush_and_close
  fi
done
