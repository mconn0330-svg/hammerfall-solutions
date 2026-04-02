#!/bin/bash
# =============================================================
# HAMMERFALL BRAIN — .md Snapshot Writer
# Reads Supabase brain and writes current memory state to .md files
# Usage: bash scripts/snapshot.sh [project] [agent]
# Run at session end or on demand
# =============================================================

PROJECT="${1:-hammerfall-solutions}"
AGENT="${2:-helm}"

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"
HAMMERFALL_DIR="$(dirname "$0")/.."

echo "Writing .md snapshot for $PROJECT/$AGENT..."

# Fetch behavioral entries
BEHAVIORAL=$(curl -s \
  "$BRAIN_URL/rest/v1/helm_memory?project=eq.$PROJECT&agent=eq.$AGENT&memory_type=eq.behavioral&order=created_at.asc" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

# Write to BEHAVIORAL_PROFILE.md
PROFILE_PATH="$HAMMERFALL_DIR/agents/$AGENT/memory/BEHAVIORAL_PROFILE.md"
echo "# Helm — Behavioral Profile (Supabase Snapshot)" > "$PROFILE_PATH"
echo "**Last snapshot:** $(date '+%Y-%m-%d %H:%M')" >> "$PROFILE_PATH"
echo "" >> "$PROFILE_PATH"

echo "$BEHAVIORAL" | python3 -c "
import sys, json
entries = json.load(sys.stdin)
for e in entries:
    print(f\"\n---\n**{e['session_date']}**\n{e['content']}\")
" >> "$PROFILE_PATH"

echo "  -> Snapshot written to $PROFILE_PATH"
git -C "$HAMMERFALL_DIR" add agents/$AGENT/memory/
git -C "$HAMMERFALL_DIR" commit -m "snapshot: $PROJECT/$AGENT — $(date +%Y-%m-%d)"
echo "  -> Snapshot committed."
