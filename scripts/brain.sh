#!/bin/bash
# =============================================================
# HAMMERFALL BRAIN — Memory Write Helper
#
# Usage:
#   bash scripts/brain.sh [project] [agent] [type] [content] [sync_ready]
#     [--table TABLE]         # default: helm_memory
#     [--strength FLOAT]      # helm_beliefs only (0.0–1.0, default 0.7)
#     [--attributes JSON]     # helm_entities only (JSONB object)
#     [--score FLOAT]         # helm_personality only (0.0–1.0)
#     [--full-content JSON]   # helm_memory only (JSONB, photographic memory layer)
#     [--confidence FLOAT]    # helm_memory only (0.0–1.0, reasoning entries — writes to dedicated column)
#     [--aliases JSON]        # helm_entities only (JSON array of alternate names e.g. '["Max","Maxie"]')
#     [--patch-id UUID]       # helm_entities only (switches POST to PATCH for updating existing row)
#     [--from-entity UUID]    # helm_entity_relationships only (required — source entity)
#     [--to-entity UUID]      # helm_entity_relationships only (required — target entity)
#     [--rel-notes TEXT]      # helm_entity_relationships only (optional — relationship context)
#     [--rel-strength FLOAT]  # helm_entity_relationships only (optional — 0.0–1.0)
#
# Type arg meaning per table (Q1 — Option B: type as semantic routing field):
#   helm_memory      → memory_type  (behavioral, scratchpad, reasoning, etc.)
#   helm_beliefs     → domain       (architecture, process, people, ethics, etc.)
#   helm_entities    → entity_type  (person, organization, concept, etc.)
#   helm_personality → attribute    (directness, verbosity, sarcasm, etc.)
#
# helm_beliefs, helm_entities, helm_personality are GLOBAL (no project/agent scope).
# project and agent args are accepted for interface consistency but not written
# to these tables. helm_memory is project/agent scoped as before.
#
# Default (no --table flag): writes to helm_memory. No existing calls break.
#
# source column on helm_beliefs always defaults to 'seeded' from brain.sh.
# learned/corrected source values are set by Phase 2 automation or direct DB update.
# =============================================================

PROJECT="$1"
AGENT="$2"
TYPE="$3"
CONTENT="$4"
SYNC_READY="${5:-false}"

# Parse optional flags
TABLE="helm_memory"
STRENGTH="0.7"
ATTRIBUTES='{}'
SCORE=""
FULL_CONTENT=""
CONFIDENCE=""
ALIASES="[]"
PATCH_ID=""
FROM_ENTITY=""
TO_ENTITY=""
REL_NOTES=""
REL_STRENGTH=""

shift 5 2>/dev/null
while [[ $# -gt 0 ]]; do
  case "$1" in
    --table)        TABLE="$2";        shift 2 ;;
    --strength)     STRENGTH="$2";     shift 2 ;;
    --attributes)   ATTRIBUTES="$2";   shift 2 ;;
    --score)        SCORE="$2";        shift 2 ;;
    --full-content) FULL_CONTENT="$2"; shift 2 ;;
    --confidence)   CONFIDENCE="$2";   shift 2 ;;
    --aliases)      ALIASES="$2";      shift 2 ;;
    --patch-id)     PATCH_ID="$2";     shift 2 ;;
    --from-entity)  FROM_ENTITY="$2";  shift 2 ;;
    --to-entity)    TO_ENTITY="$2";    shift 2 ;;
    --rel-notes)    REL_NOTES="$2";    shift 2 ;;
    --rel-strength) REL_STRENGTH="$2"; shift 2 ;;
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

# --patch-id guard: only supported for helm_entities — check before payload construction
if [ -n "$PATCH_ID" ] && [ "$TABLE" != "helm_entities" ]; then
  echo "ERROR: --patch-id is only supported for --table helm_entities."
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
    if [ -n "$FULL_CONTENT" ] && [ -n "$CONFIDENCE" ]; then
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s,"full_content":%s,"confidence":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" "$FULL_CONTENT" "$CONFIDENCE" > "$TMPFILE"
    elif [ -n "$FULL_CONTENT" ]; then
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s,"full_content":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" "$FULL_CONTENT" > "$TMPFILE"
    elif [ -n "$CONFIDENCE" ]; then
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s,"confidence":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" "$CONFIDENCE" > "$TMPFILE"
    else
      printf '{"project":"%s","agent":"%s","memory_type":"%s","content":%s,"sync_ready":%s}' \
        "$PROJECT" "$AGENT" "$TYPE" "$ESCAPED" "$SYNC_READY" > "$TMPFILE"
    fi
    ;;

  helm_beliefs)
    # Global table — no project/agent. type arg = domain. content arg = belief text.
    printf '{"domain":"%s","belief":%s,"strength":%s,"active":true,"source":"seeded"}' \
      "$TYPE" "$ESCAPED" "$STRENGTH" > "$TMPFILE"
    ;;

  helm_entities)
    # Global table — no project/agent. type arg = entity_type. content arg = entity name.
    # --patch-id: switches to PATCH for updating an existing row (e.g. appending aliases).
    # --patch-id is only valid for helm_entities — guard enforced below before curl.
    if [ -n "$PATCH_ID" ]; then
      # PATCH payload: only include fields being updated (aliases array replacement)
      printf '{"aliases":%s}' "$ALIASES" > "$TMPFILE"
    else
      printf '{"entity_type":"%s","name":%s,"attributes":%s,"aliases":%s,"active":true}' \
        "$TYPE" "$ESCAPED" "$ATTRIBUTES" "$ALIASES" > "$TMPFILE"
    fi
    ;;

  helm_personality)
    # Global table — no project/agent. type arg = attribute. content arg = description note.
    # Uses upsert (ON CONFLICT attribute DO UPDATE) — attribute is UNIQUE, only one row per attribute.
    if [ -z "$SCORE" ]; then
      echo "ERROR: --score required for helm_personality writes."
      rm -f "$TMPFILE"
      exit 1
    fi
    printf '{"attribute":"%s","score":%s,"description":%s}' \
      "$TYPE" "$SCORE" "$ESCAPED" > "$TMPFILE"
    ;;

  helm_entity_relationships)
    # Global table — no project/agent. type arg = relationship label.
    # content arg unused. Requires --from-entity and --to-entity UUIDs.
    # --rel-notes TEXT (optional, defaults null)
    # --rel-strength FLOAT (optional, defaults null)
    if [ -z "$FROM_ENTITY" ] || [ -z "$TO_ENTITY" ]; then
      echo "ERROR: --from-entity and --to-entity are required for helm_entity_relationships writes."
      rm -f "$TMPFILE"
      exit 1
    fi
    if [ -n "$REL_NOTES" ]; then
      ESCAPED_NOTES=$(node -e "
        let d = '';
        process.stdin.on('data', c => d += c);
        process.stdin.on('end', () => process.stdout.write(JSON.stringify(d)));
      " <<< "$REL_NOTES")
    else
      ESCAPED_NOTES="null"
    fi
    if [ -n "$REL_STRENGTH" ]; then
      if [ -n "$REL_NOTES" ]; then
        printf '{"from_entity":"%s","to_entity":"%s","relationship":"%s","notes":%s,"active":true,"strength":%s}' \
          "$FROM_ENTITY" "$TO_ENTITY" "$TYPE" "$ESCAPED_NOTES" "$REL_STRENGTH" > "$TMPFILE"
      else
        printf '{"from_entity":"%s","to_entity":"%s","relationship":"%s","notes":null,"active":true,"strength":%s}' \
          "$FROM_ENTITY" "$TO_ENTITY" "$TYPE" "$REL_STRENGTH" > "$TMPFILE"
      fi
    else
      printf '{"from_entity":"%s","to_entity":"%s","relationship":"%s","notes":%s,"active":true}' \
        "$FROM_ENTITY" "$TO_ENTITY" "$TYPE" "$ESCAPED_NOTES" > "$TMPFILE"
    fi
    ;;

  *)
    echo "ERROR: Unknown --table value: $TABLE"
    echo "Valid tables: helm_memory, helm_beliefs, helm_entities, helm_personality, helm_entity_relationships"
    rm -f "$TMPFILE"
    exit 1
    ;;

esac

# --ssl-no-revoke: required on Windows/schannel to bypass certificate revocation check
# helm_personality uses upsert — UNIQUE constraint on attribute means only one row per attribute
# helm_entity_relationships uses plain POST — no unique constraint, bidirectional rows written separately
# helm_entities with --patch-id uses PATCH to update existing row by UUID
if [ -n "$PATCH_ID" ]; then
  RESPONSE=$(curl -s --ssl-no-revoke -X PATCH \
    "$BRAIN_URL/rest/v1/helm_entities?id=eq.$PATCH_ID" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d @"$TMPFILE")
elif [ "$TABLE" = "helm_personality" ]; then
  # on_conflict=attribute tells PostgREST to upsert on the UNIQUE attribute column
  RESPONSE=$(curl -s --ssl-no-revoke -X POST \
    "$BRAIN_URL/rest/v1/$TABLE?on_conflict=attribute" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation,resolution=merge-duplicates" \
    -d @"$TMPFILE")
else
  RESPONSE=$(curl -s --ssl-no-revoke -X POST \
    "$BRAIN_URL/rest/v1/$TABLE" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d @"$TMPFILE")
fi
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
  if [ "$TABLE" = "helm_entity_relationships" ]; then
    echo "  -> Relationship written: [$TABLE] $FROM_ENTITY --[$TYPE]--> $TO_ENTITY"
  elif [ -n "$PATCH_ID" ]; then
    echo "  -> Entity updated: [$TABLE] id=$PATCH_ID"
  else
    echo "  -> Memory written: [$TABLE/$TYPE] sync_ready=$SYNC_READY"
  fi
fi
