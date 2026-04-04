#!/bin/bash
# =============================================================
# HAMMERFALL — Activity Ping
# Resets the session inactivity timer without incrementing the message counter.
# Call before/after any tool use or long-running operation.
# This prevents the session watchdog from firing during active build tasks.
#
# Usage: bash scripts/activity_ping.sh [project] [agent]
# Model-agnostic — any model that can run a shell command can emit this signal.
# =============================================================

PROJECT="${1:-hammerfall-solutions}"
AGENT="${2:-helm}"

SESSION_DIR="/tmp/hammerfall_session"
PING_FILE="$SESSION_DIR/last_ping_${PROJECT}_${AGENT}"

mkdir -p "$SESSION_DIR"
date +%s > "$PING_FILE"
