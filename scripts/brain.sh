#!/bin/bash
# =============================================================
# HAMMERFALL BRAIN — Memory Write Helper
#
# Usage:
#   bash scripts/brain.sh [project] [agent] [type] [content] [sync_ready]
#     [--table TABLE]           # default: helm_memory
#     [--strength FLOAT]        # helm_beliefs only (0.0–1.0, default 0.9)
#     [--attributes JSON]       # helm_entities only (JSONB object)
#     [--score FLOAT]           # helm_personality only (0.0–1.0)
#     [--full-content JSON]     # helm_memory only (JSONB object)
#
# Type arg meaning per table:
#   helm_memory     → memory_type  (behavioral, scratchpad, reasoning, etc.)
#   helm_beliefs    → domain       (architecture, process, people, ethics, etc.)
#   helm_entities   → entity_type  (person, organization, concept, etc.)
#   helm_personality → attribute   (directness, verbosity, sarcasm, etc.)
#
# Default (no --table flag): writes to helm_memory. No existing calls break.
# =============================================================

PROJECT="$1"
AGENT="$2"
TYPE="$3"
CONTENT="$4"
SYNC_READY="${5:-false}"

# Parse optional flags
TABLE="helm_memory"
STRENGTH="0.9"
ATTRIBUTES='{}'
SCORE=""
FULL_CONTENT=""

shift 5 2>/dev/null
while [[ $# -gt 0 ]]; do
  case "$1" in
    --table)        TABLE="$2";        shift 2 ;;
    --strength)     STRENGTH="$2";     shift 2 ;;
    --attributes)   ATTRIBUTES="$2";   shift 2 ;;
    --score)        SCORE="$2";        shift 2 ;;
    --full-content) FULL_CONTENT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"

if [ -z "$BRAIN_URL" ] || [ -z "$SERVICE_KEY" ]; then
  echo "ERROR: Brain URL or service key not configured."
  echo "Check hammerfall-config.md and env vars."
  exit 1
fi

# Escape content string for JSON
ESCAPED=$(node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => process.stdout.write(JSON.stringify(d)));
" <<< "$CONTENT")

# Write JSON to temp file — avoids Windows/Git Bash multi-byte UTF-8 corruption
TMPFILE=$(mktemp /tmp/brain_write_XXXXXX.json)

case "$TABLE" in

  helm_memory)
    if [ -n "$FULL_CONTENT" ]; then
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s,"full_content":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" "$FULL_CONTENT" > "$TMPFILE"
    else
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" > "$TMPFILE"
    fi
    ;;

  helm_beliefs)
    printf '{"project":"%s","agent":"%s","domain":"%s","content":%s,"strength":%s,"sync_ready":%s,"active":true}' \
      "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$STRENGTH" "$SYNC_READY" > "$TMPFILE"
    ;;

  helm_entities)
    # content arg = entity name; attributes passed via --attributes flag
    ESCAPED_NAME="$ESCAPED"
    printf '{"project":"%s","agent":"%s","entity_type":"%s","name":%s,"attributes":%s,"sync_ready":%s}' \
      "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED_NAME" "$ATTRIBUTES" "$SYNC_READY" > "$TMPFILE"
    ;;

  helm_personality)
    if [ -z "$SCORE" ]; then
      echo "ERROR: --score required for helm_personality writes."
      rm -f "$TMPFILE"
      exit 1
    fi
    printf '{"project":"%s","agent":"%s","attribute":"%s","score":%s,"note":%s}' \
      "$PROJECT" "$AGENT" "$TYPE" "$SCORE" "$ESCAPED" > "$TMPFILE"
    ;;

  *)
    echo "ERROR: Unknown --table value: $TABLE"
    echo "Valid tables: helm_memory, helm_beliefs, helm_entities, helm_personality"
    rm -f "$TMPFILE"
    exit 1
    ;;

esac

# --ssl-no-revoke: required on Windows/schannel to bypass certificate revocation check
RESPONSE=$(curl -s --ssl-no-revoke -X POST \
  "$BRAIN_URL/rest/v1/$TABLE" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d @"$TMPFILE")
rm -f "$TMPFILE"

# Check response body for errors — curl exit code is 0 on HTTP errors, so $? alone is insufficient
if echo "$RESPONSE" | grep -q '"code"'; then
  echo "  ERROR: Brain write failed — $(echo "$RESPONSE" | grep -o '"message":"[^"]*"')"
  if [ "$TABLE" = "helm_memory" ]; then
    echo "  Falling back to .md append."
    echo "" >> "agents/$AGENT/memory/BEHAVIORAL_PROFILE.md"
    echo "$(date +%Y-%m-%d) | $CONTENT" >> "agents/$AGENT/memory/BEHAVIORAL_PROFILE.md"
  fi
else
  echo "  -> Memory written: [$PROJECT/$AGENT/$TABLE/$TYPE] sync_ready=$SYNC_READY"
fi
