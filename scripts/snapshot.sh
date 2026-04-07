#!/bin/bash
# =============================================================
# HAMMERFALL BRAIN — .md Snapshot Writer
#
# Reads Supabase brain and writes current memory state to .md files.
# Usage: bash scripts/snapshot.sh [project] [agent]
# Run at session end or on demand via Routine 5.
#
# Outputs:
#   agents/[agent]/memory/BEHAVIORAL_PROFILE.md   — all behavioral entries (existing)
#   agents/[agent]/memory/BRAIN_SUMMARY.md         — warm layer: per-category summaries
#   agents/[agent]/memory/BELIEFS_SUMMARY.md       — warm layer: all active beliefs
#   agents/[agent]/memory/PERSONALITY_SUMMARY.md   — warm layer: all personality scores
#
# Token approximation: character_count / 4 (standard English prose approximation).
# Warm layer target: under 1,200 tokens (~4,800 chars) per summary file.
# =============================================================

PROJECT="${1:-hammerfall-solutions}"
AGENT="${2:-helm}"

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"
HAMMERFALL_DIR="$(dirname "$0")/.."
MEMORY_DIR="$HAMMERFALL_DIR/agents/$AGENT/memory"

echo "Writing .md snapshot for $PROJECT/$AGENT..."

# Helper: check token budget for a file
# Usage: check_token_budget FILE_PATH LABEL
check_token_budget() {
  local file="$1"
  local label="$2"
  if [ -f "$file" ]; then
    local char_count
    char_count=$(wc -c < "$file")
    local token_estimate=$(( char_count / 4 ))
    if [ "$token_estimate" -gt 1200 ]; then
      echo "  WARN: $label estimated at $token_estimate tokens (>${char_count} chars) — exceeds 1,200 token warm layer target"
    else
      echo "  -> $label: ~$token_estimate tokens (${char_count} chars)"
    fi
  fi
}

# --ssl-no-revoke: required on Windows/schannel
# =============================================================
# 1. BEHAVIORAL_PROFILE.md — existing format, unchanged
# =============================================================
BEHAVIORAL=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_memory?project=eq.$PROJECT&agent=eq.$AGENT&memory_type=eq.behavioral&order=created_at.asc" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

PROFILE_PATH="$MEMORY_DIR/BEHAVIORAL_PROFILE.md"
echo "# Helm — Behavioral Profile (Supabase Snapshot)" > "$PROFILE_PATH"
echo "**Last snapshot:** $(date '+%Y-%m-%d %H:%M')" >> "$PROFILE_PATH"
echo "" >> "$PROFILE_PATH"

echo "$BEHAVIORAL" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    const entries = JSON.parse(d);
    entries.forEach(e => process.stdout.write('\n---\n**' + e.session_date + '**\n' + e.content + '\n'));
  });
" >> "$PROFILE_PATH"

echo "  -> BEHAVIORAL_PROFILE.md written ($(wc -l < "$PROFILE_PATH") lines)"

# =============================================================
# 2. BRAIN_SUMMARY.md — warm layer: per-category summaries
#    One paragraph per helm_memory_index category from 10 most recent entries.
# =============================================================
BRAIN_SUMMARY_PATH="$MEMORY_DIR/BRAIN_SUMMARY.md"
echo "# Brain Summary — Warm Layer (Supabase Snapshot)" > "$BRAIN_SUMMARY_PATH"
echo "**Last snapshot:** $(date '+%Y-%m-%d %H:%M')" >> "$BRAIN_SUMMARY_PATH"
echo "**Project:** $PROJECT | **Agent:** $AGENT" >> "$BRAIN_SUMMARY_PATH"
echo "" >> "$BRAIN_SUMMARY_PATH"
echo "_10 most recent entries per category. Full entries queryable via Routine 6._" >> "$BRAIN_SUMMARY_PATH"
echo "" >> "$BRAIN_SUMMARY_PATH"

# Fetch all categories from index
CATEGORIES=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_memory_index?project=eq.$PROJECT&agent=eq.helm&select=category,summary" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

# For each category, fetch 10 most recent entries and write section
echo "$CATEGORIES" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    const cats = JSON.parse(d);
    process.stdout.write(JSON.stringify(cats.map(c => c.category)));
  });
" | while IFS= read -r CATS_JSON; do
  # Parse category list and loop
  echo "$CATS_JSON" | node -e "
    let d = '';
    process.stdin.on('data', c => d += c);
    process.stdin.on('end', () => {
      JSON.parse(d).forEach(cat => process.stdout.write(cat + '\n'));
    });
  " | while IFS= read -r CATEGORY; do
    [ -z "$CATEGORY" ] && continue

    # Fetch 10 most recent entries for this category
    ENTRIES=$(curl -s --ssl-no-revoke \
      "$BRAIN_URL/rest/v1/helm_memory?project=eq.$PROJECT&agent=eq.$AGENT&memory_type=eq.$CATEGORY&order=created_at.desc&limit=10" \
      -H "apikey: $SERVICE_KEY" \
      -H "Authorization: Bearer $SERVICE_KEY")

    ENTRY_COUNT=$(echo "$ENTRIES" | node -e "
      let d='';process.stdin.on('data',c=>d+=c);
      process.stdin.on('end',()=>process.stdout.write(String(JSON.parse(d).length)));
    ")

    [ "$ENTRY_COUNT" = "0" ] && continue

    echo "## $CATEGORY ($ENTRY_COUNT entries)" >> "$BRAIN_SUMMARY_PATH"
    echo "" >> "$BRAIN_SUMMARY_PATH"

    echo "$ENTRIES" | node -e "
      let d = '';
      process.stdin.on('data', c => d += c);
      process.stdin.on('end', () => {
        const entries = JSON.parse(d);
        entries.forEach(e => {
          const date = e.created_at ? e.created_at.substring(0,10) : e.session_date;
          process.stdout.write('- [' + date + '] ' + e.content + '\n');
        });
      });
    " >> "$BRAIN_SUMMARY_PATH"

    echo "" >> "$BRAIN_SUMMARY_PATH"
  done
done

check_token_budget "$BRAIN_SUMMARY_PATH" "BRAIN_SUMMARY.md"

# =============================================================
# 3. BELIEFS_SUMMARY.md — warm layer: all active beliefs
# =============================================================
BELIEFS=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_beliefs?active=eq.true&order=strength.desc" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

BELIEFS_PATH="$MEMORY_DIR/BELIEFS_SUMMARY.md"
echo "# Helm — Beliefs Summary (Supabase Snapshot)" > "$BELIEFS_PATH"
echo "**Last snapshot:** $(date '+%Y-%m-%d %H:%M')" >> "$BELIEFS_PATH"
echo "" >> "$BELIEFS_PATH"
echo "_Strength scale: 0.9–1.0 = near-prime directives | 0.7–0.9 = firmly held | 0.4–0.6 = working assumptions | 0.1–0.3 = hypotheses_" >> "$BELIEFS_PATH"
echo "" >> "$BELIEFS_PATH"

echo "$BELIEFS" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    const entries = JSON.parse(d);
    if (entries.length === 0) {
      process.stdout.write('_No active beliefs seeded yet._\n');
      return;
    }
    let currentDomain = '';
    entries.forEach(e => {
      if (e.domain !== currentDomain) {
        currentDomain = e.domain;
        process.stdout.write('\n## ' + currentDomain + '\n\n');
      }
      process.stdout.write('- **[' + e.strength.toFixed(2) + ']** ' + e.belief + '\n');
    });
  });
" >> "$BELIEFS_PATH"

check_token_budget "$BELIEFS_PATH" "BELIEFS_SUMMARY.md"

# =============================================================
# 4. PERSONALITY_SUMMARY.md — warm layer: all personality scores
# =============================================================
PERSONALITY=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_personality?order=attribute.asc" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY")

PERSONALITY_PATH="$MEMORY_DIR/PERSONALITY_SUMMARY.md"
echo "# Helm — Personality Scores (Supabase Snapshot)" > "$PERSONALITY_PATH"
echo "**Last snapshot:** $(date '+%Y-%m-%d %H:%M')" >> "$PERSONALITY_PATH"
echo "" >> "$PERSONALITY_PATH"
echo "_Score scale: 0.0–1.0. Apply these at session start — not background data, active operating parameters._" >> "$PERSONALITY_PATH"
echo "" >> "$PERSONALITY_PATH"

echo "$PERSONALITY" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    const entries = JSON.parse(d);
    if (entries.length === 0) {
      process.stdout.write('_No personality scores set yet._\n');
      return;
    }
    entries.forEach(e => {
      const desc = (e.description || '').replace(/[\r\n]+/g, ' ').trim();
      process.stdout.write('| ' + e.attribute.padEnd(22) + ' | ' + e.score.toFixed(2) + ' | ' + desc + ' |\n');
    });
  });
" >> "$PERSONALITY_PATH"

check_token_budget "$PERSONALITY_PATH" "PERSONALITY_SUMMARY.md"

# =============================================================
# Commit snapshot
# =============================================================
echo ""
git -C "$HAMMERFALL_DIR" add agents/$AGENT/memory/
git -C "$HAMMERFALL_DIR" commit -m "snapshot: $PROJECT/$AGENT — $(date +%Y-%m-%d)"
echo "  -> Snapshot committed."
