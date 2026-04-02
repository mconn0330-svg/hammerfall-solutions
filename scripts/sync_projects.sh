#!/bin/bash
# =============================================================
# HAMMERFALL SOLUTIONS — CORE HELM SYNC SCRIPT
# Post-migration: repurposed as brain status check and snapshot trigger.
# The brain is shared — no file-based data relay required.
#
# Usage: bash scripts/sync_projects.sh
# Trigger: "Helm, sync now" or scheduled (7 AM, 12 PM, 6 PM)
# =============================================================
set -e

HAMMERFALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SYNC_DATE="$(date +%Y-%m-%d)"
SYNC_TIME="$(date +%H:%M)"

echo "============================================"
echo "CORE HELM SYNC — $SYNC_DATE $SYNC_TIME"
echo "============================================"

# Post-migration: sync is now a status check and snapshot trigger
# The brain is shared — no data relay required

CONFIG_FILE="$HAMMERFALL_DIR/hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"

echo "== Hammerfall Brain Status Check — $(date '+%Y-%m-%d %H:%M') =="

# Query recent brain activity across all projects
RECENT=$(curl -s \
  "$BRAIN_URL/rest/v1/helm_memory?order=created_at.desc&limit=20&select=project,agent,memory_type,content,created_at" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

echo "$RECENT" | python3 -c '
import sys, json
entries = json.load(sys.stdin)
print(f"Recent brain entries: {len(entries)}")
for e in entries:
    print(f"  [{e[\"created_at\"][:16]}] {e[\"project\"]}/{e[\"agent\"]} ({e[\"memory_type\"]}): {e[\"content\"][:80]}")
'

# Trigger .md snapshot for hammerfall-solutions
bash "$(dirname "$0")/snapshot.sh" hammerfall-solutions helm

echo "== Status check complete =="
