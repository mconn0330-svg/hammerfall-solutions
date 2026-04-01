#!/bin/bash
# =============================================================
# HAMMERFALL SOLUTIONS — CORE HELM SYNC SCRIPT
# Reads active-projects.md and syncs Project Helm memories
# upward to Core Helm in hammerfall-solutions.
#
# Usage: bash scripts/sync_projects.sh
# Trigger: "Helm, sync now" or scheduled (7 AM, 12 PM, 6 PM)
# =============================================================
set -e

HAMMERFALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTIVE_PROJECTS="$HAMMERFALL_DIR/active-projects.md"
CORE_PROFILE="$HAMMERFALL_DIR/agents/helm/memory/BEHAVIORAL_PROFILE.md"
CORE_INDEX="$HAMMERFALL_DIR/agents/helm/memory/LongTerm/MEMORY_INDEX.md"
SYNC_DATE="$(date +%Y-%m-%d)"
SYNC_TIME="$(date +%H:%M)"
SYNC_ENTRIES=0
SYNC_ERRORS=0
PROJECTS_SYNCED=""

echo "============================================"
echo "CORE HELM SYNC — $SYNC_DATE $SYNC_TIME"
echo "============================================"

# Validate active-projects.md exists
if [ ! -f "$ACTIVE_PROJECTS" ]; then
  echo "ERROR: active-projects.md not found at $ACTIVE_PROJECTS"
  exit 1
fi

# Parse active projects (skip header lines, only process table rows with "active")
while IFS='|' read -r _ codename repo_path launch_date status _; do
  # Trim whitespace
  codename="$(echo "$codename" | xargs)"
  repo_path="$(echo "$repo_path" | xargs)"
  status="$(echo "$status" | xargs)"

  # Skip header, separator, and non-active rows
  [[ "$codename" == "Codename" ]] && continue
  [[ "$codename" == "---" ]] && continue
  [[ -z "$codename" ]] && continue
  [[ "$status" != *"active"* ]] && continue

  # Resolve repo path relative to hammerfall-solutions
  FULL_REPO_PATH="$HAMMERFALL_DIR/$repo_path"

  echo ""
  echo "--- Syncing: $codename ($FULL_REPO_PATH) ---"

  # Check if repo exists
  if [ ! -d "$FULL_REPO_PATH" ]; then
    echo "  WARNING: Repo not found at $FULL_REPO_PATH. Skipping."
    SYNC_ERRORS=$((SYNC_ERRORS + 1))
    continue
  fi

  PROJECT_PROFILE="$FULL_REPO_PATH/agents/helm/memory/BEHAVIORAL_PROFILE.md"
  PROJECT_SCRATCHPAD="$FULL_REPO_PATH/agents/helm/memory/ShortTerm_Scratchpad.md"

  # Read Project Helm BEHAVIORAL_PROFILE.md
  if [ -f "$PROJECT_PROFILE" ]; then
    # Check for [SYNC-READY] entries
    SYNC_READY_ENTRIES=$(grep -c "\[SYNC-READY\]" "$PROJECT_PROFILE" 2>/dev/null || true)
    if [ "$SYNC_READY_ENTRIES" -gt 0 ]; then
      echo "  -> Found $SYNC_READY_ENTRIES [SYNC-READY] entries in BEHAVIORAL_PROFILE.md"

      # Append sync-ready entries to Core Helm profile
      echo "" >> "$CORE_PROFILE"
      echo "### Sync from $codename — $SYNC_DATE $SYNC_TIME" >> "$CORE_PROFILE"
      grep "\[SYNC-READY\]" "$PROJECT_PROFILE" >> "$CORE_PROFILE"
      SYNC_ENTRIES=$((SYNC_ENTRIES + SYNC_READY_ENTRIES))
    else
      echo "  -> No [SYNC-READY] entries found. Skipping profile sync."
    fi
  else
    echo "  WARNING: No BEHAVIORAL_PROFILE.md found for $codename."
    SYNC_ERRORS=$((SYNC_ERRORS + 1))
  fi

  # Read Project Helm ShortTerm_Scratchpad.md for active context
  if [ -f "$PROJECT_SCRATCHPAD" ]; then
    SCRATCHPAD_LINES=$(wc -l < "$PROJECT_SCRATCHPAD" | xargs)
    if [ "$SCRATCHPAD_LINES" -gt 5 ]; then
      echo "  -> Scratchpad has $SCRATCHPAD_LINES lines (active session detected)."
    else
      echo "  -> Scratchpad is empty or minimal."
    fi
  fi

  PROJECTS_SYNCED="$PROJECTS_SYNCED $codename"

done < "$ACTIVE_PROJECTS"

# Update MEMORY_INDEX.md
if [ "$SYNC_ENTRIES" -gt 0 ]; then
  echo "$SYNC_DATE | Core sync | Synced $SYNC_ENTRIES entries from:$PROJECTS_SYNCED" >> "$CORE_INDEX"
fi

# Safeguard: skip commit if working tree already has uncommitted changes in memory/
# Prevents non-fast-forward conflicts during scheduled syncs
# grep -v "^??" excludes untracked files — only tracked modified files block the commit
DIRTY_CHECK=$(git status --porcelain agents/helm/memory/ 2>/dev/null | grep -v "^??" || true)
if [ -n "$DIRTY_CHECK" ]; then
  echo ""
  echo "WARNING: Working tree has uncommitted changes in agents/helm/memory/"
  echo "Skipping sync commit to avoid non-fast-forward conflicts."
  echo "Changes will be captured on the next scheduled sync."
  exit 0
fi

# Commit if changes were made
cd "$HAMMERFALL_DIR"
if [ -n "$(git status --porcelain agents/helm/memory/)" ]; then
  git add agents/helm/memory/
  git commit -m "memory: core sync — $SYNC_DATE $SYNC_TIME"
  echo ""
  echo "Changes committed."
else
  echo ""
  echo "No changes to commit."
fi

# Summary
echo ""
echo "============================================"
echo "SYNC COMPLETE"
echo "============================================"
echo "Projects scanned:$PROJECTS_SYNCED"
echo "Entries synced: $SYNC_ENTRIES"
echo "Errors: $SYNC_ERRORS"
echo "============================================"
