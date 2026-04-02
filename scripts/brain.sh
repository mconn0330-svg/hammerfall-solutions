#!/bin/bash
# =============================================================
# HAMMERFALL BRAIN — Memory Write Helper
# Usage: bash scripts/brain.sh [project] [agent] [type] [content] [sync_ready]
# sync_ready: true or false
# =============================================================

PROJECT="$1"
AGENT="$2"
TYPE="$3"
CONTENT="$4"
SYNC_READY="${5:-false}"

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"

if [ -z "$BRAIN_URL" ] || [ -z "$SERVICE_KEY" ]; then
  echo "ERROR: Brain URL or service key not configured."
  echo "Check hammerfall-config.md and env vars."
  exit 1
fi

# Escape content for JSON
ESCAPED=$(node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => process.stdout.write(JSON.stringify(d)));
" <<< "$CONTENT")

# --ssl-no-revoke: required on Windows/schannel to bypass certificate revocation check
# Write to Supabase
RESPONSE=$(curl -s --ssl-no-revoke -X POST \
  "$BRAIN_URL/rest/v1/helm_memory" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d "{\"project\":\"$PROJECT\",\"agent\":\"$AGENT\",\"memory_type\":\"$TYPE\",\"content\":$ESCAPED,\"sync_ready\":$SYNC_READY}")

if [ $? -eq 0 ]; then
  echo "  -> Memory written: [$PROJECT/$AGENT/$TYPE] sync_ready=$SYNC_READY"
else
  echo "  ERROR: Failed to write memory. Falling back to .md append."
  # Fallback: append to BEHAVIORAL_PROFILE.md
  echo "" >> "agents/$AGENT/memory/BEHAVIORAL_PROFILE.md"
  echo "$(date +%Y-%m-%d) | $CONTENT" >> "agents/$AGENT/memory/BEHAVIORAL_PROFILE.md"
fi
