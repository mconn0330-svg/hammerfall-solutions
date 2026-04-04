#!/bin/bash
# =============================================================
# HAMMERFALL — Session Ping
# Called by agent after every response.
# Tracks message count and last activity timestamp.
# Fires brain.sh heartbeat at message 10 unconditionally.
#
# Usage: bash scripts/ping_session.sh [project] [agent]
# Add to every agent prompt: "After every response, run: bash scripts/ping_session.sh [project] [agent]"
# =============================================================

PROJECT="${1:-hammerfall-solutions}"
AGENT="${2:-helm}"

HAMMERFALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_DIR="/tmp/hammerfall_session"
COUNTER_FILE="$SESSION_DIR/msg_count_${PROJECT}_${AGENT}"
PING_FILE="$SESSION_DIR/last_ping_${PROJECT}_${AGENT}"

# Ensure session dir exists
mkdir -p "$SESSION_DIR"

# Update last ping timestamp
date +%s > "$PING_FILE"

# Increment message counter
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo $COUNT > "$COUNTER_FILE"

# At message 10 — fire heartbeat unconditionally and reset counter
if [ "$COUNT" -ge 10 ]; then
  echo 0 > "$COUNTER_FILE"
  bash "$HAMMERFALL_DIR/scripts/brain.sh" "$PROJECT" "$AGENT" "scratchpad" "HEARTBEAT — auto-triggered at message 10 by ping_session.sh" false
fi
