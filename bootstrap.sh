#!/bin/bash
# =============================================================
# HAMMERFALL SOLUTIONS — AUTONOMOUS PROJECT BOOTSTRAPPER v4.1
# Executed by: Helm (Technical Director)
# Architecture: IDE-First, Repo-Brain, Project Helm Clone
# Changes from v4: Full Supabase auto-creation via hammerfall-config.md
#                  Unique DB password generated per project via openssl rand
# =============================================================
set -e

# ── Self-Healing Bash Resolver ────────────────────────────────
# Dynamically derives Git Bash path via 'where git' to handle
# non-standard install locations. Re-invokes via Git Bash if
# running under Windows system bash or MINGW/CYGWIN environments.
_UNAME="$(uname -s 2>/dev/null || echo unknown)"
if [[ "$_UNAME" == MINGW* ]] || [[ "$_UNAME" == CYGWIN* ]] || \
   { [ -n "$WINDIR" ] && [ "$_UNAME" = "Linux" ] && \
     grep -qi "microsoft" /proc/version 2>/dev/null; }; then
  GIT_BASH="$(where git 2>/dev/null | head -1 | \
    sed 's|\\cmd\\git.exe|\\bin\\bash.exe|')"
  if [ -n "$GIT_BASH" ] && [ -f "$GIT_BASH" ]; then
    echo "Re-invoking via Git Bash: $GIT_BASH"
    exec "$GIT_BASH" "$0" "$@"
  else
    echo "WARNING: Could not locate Git Bash dynamically. Proceeding with current shell."
  fi
fi

# ── 1. Parameter Validation ───────────────────────────────────
PROJECT_NAME=$1
if [ -z "$PROJECT_NAME" ]; then
  echo "ERROR: Project codename required."
  echo "Usage: ./bootstrap.sh [codename]"
  exit 1
fi

HAMMERFALL_DIR="$(pwd)"
PROJECT_DIR="../Hammerfall-$PROJECT_NAME"
CONFIG_FILE="$HAMMERFALL_DIR/hammerfall-config.md"

echo "============================================"
echo "INITIATING LAUNCH SEQUENCE FOR: $PROJECT_NAME"
echo "============================================"

# ── 2. Read hammerfall-config.md ──────────────────────────────
echo "[0/13] Reading hammerfall-config.md..."
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: hammerfall-config.md not found at $CONFIG_FILE"
  echo "Create it before running bootstrap. See README.md for instructions."
  exit 1
fi

# Parse config values
GITHUB_USER=$(grep "hammerfall_github_user:" "$CONFIG_FILE" | awk '{print $2}')
SUPABASE_ORG_ID=$(grep "supabase_org_id:" "$CONFIG_FILE" | awk '{print $2}')
SUPABASE_REGION=$(grep "supabase_region:" "$CONFIG_FILE" | awk '{print $2}')

# Generate a unique cryptographically random DB password for this project
# Each project gets its own password — never reused, never stored in config
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Validate required values
if [ -z "$SUPABASE_ORG_ID" ] || [ "$SUPABASE_ORG_ID" = "[paste" ]; then
  echo "ERROR: supabase_org_id not set in hammerfall-config.md"
  echo "Run: supabase orgs list — paste your org ID into hammerfall-config.md"
  exit 1
fi

echo "  -> Config loaded."
echo "  -> GitHub user: $GITHUB_USER"
echo "  -> Supabase org: $SUPABASE_ORG_ID | Region: $SUPABASE_REGION"

# ── 3. Scaffold from Master Template ─────────────────────────
echo "[1/13] Scaffolding from project_structure_template..."
cp -r "$HAMMERFALL_DIR/project_structure_template" "$PROJECT_DIR"
cd "$PROJECT_DIR"

# ── 4. Inject Project Helm Clone ─────────────────────────────
echo "[2/13] Cloning Project Helm into repo..."
mkdir -p agents/helm/memory/LongTerm
cp "$HAMMERFALL_DIR/agents/helm/helm_prompt.md" agents/helm/helm_prompt.md
echo "  -> Project Helm cloned from Core Helm at $(date +%Y-%m-%d)"

sed -i "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" agents/helm/helm_prompt.md

cat > agents/helm/memory/ShortTerm_Scratchpad.md << EOF
# Project Helm — ShortTerm Scratchpad (Supabase Snapshot)
**Project:** $PROJECT_NAME
**Last flushed:** $(date +%Y-%m-%d)

This file is a read-only snapshot. Active working memory lives in the Supabase brain.
All writes go through scripts/brain.sh.
EOF

cat > agents/helm/memory/BEHAVIORAL_PROFILE.md << EOF
# Project Helm — Behavioral Profile (Supabase Snapshot)
**Project:** $PROJECT_NAME
**Created:** $(date +%Y-%m-%d)

This file is a read-only snapshot written by snapshot.sh.
Do not write here directly. All memory writes go through scripts/brain.sh.
EOF

cat > agents/helm/memory/LongTerm/MEMORY_INDEX.md << EOF
# Project Helm — Long Term Memory Index
**Project:** $PROJECT_NAME

One-line entry per archived event. Format: YYYY-MM-DD | [topic] | [brief summary]
EOF

# ── 5. Inject Project Rules ───────────────────────────────────
echo "[3/13] Injecting PROJECT_RULES.md..."
if [ -f "Project_Rules" ]; then
  mv Project_Rules PROJECT_RULES.md
elif [ ! -f "PROJECT_RULES.md" ]; then
  echo "  WARNING: No Project_Rules file found in template. Skipping."
fi

# ── 6. Inject Replit Instructions ─────────────────────────────
echo "[4/13] Injecting REPLIT_INSTRUCTIONS.md..."
if [ ! -f "REPLIT_INSTRUCTIONS.md" ]; then
  cp "$HAMMERFALL_DIR/project_structure_template/REPLIT_INSTRUCTIONS.md" . \
  2>/dev/null || echo "  WARNING: REPLIT_INSTRUCTIONS.md not found in master repo."
fi

# ── 7. Inject Staged Specs ────────────────────────────────────
echo "[5/13] Checking for staged specs..."
STAGING_DIR="$HAMMERFALL_DIR/staging_area/$PROJECT_NAME"
if [ -d "$STAGING_DIR" ] && [ "$(ls -A "$STAGING_DIR" 2>/dev/null)" ]; then
  echo "  -> Found specs for $PROJECT_NAME. Copying to specs/ready/..."
  mkdir -p specs/ready
  cp "$STAGING_DIR"/* ./specs/ready/
  echo "  -> Specs injected."
else
  echo "  -> No staged specs found for $PROJECT_NAME. Continuing."
fi

# ── 8. Create SITREPs folder and TASKS.md ────────────────────
echo "[6/13] Creating SITREPs folder and TASKS.md..."
mkdir -p SITREPs

cat > SITREPs/TASKS.md << EOF
# TASKS — $PROJECT_NAME

**Canonical task file. All agents read and write here.**
**Location:** SITREPs/TASKS.md (do not move or duplicate)

## Format
Each task: | ID | Task | Owner | Status | Notes |
Status values: Todo | In Progress | Done | Blocked

## Current Sprint

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| T001 | Connect Replit to replit/ui-v1 and build frontend | Replit Agent | Todo | Read REPLIT_INSTRUCTIONS.md first |
| T002 | UX Lead adoption report | UX Lead | Todo | Review replit/ui-v1 components |
| T003 | BE Dev: Supabase schema and wiring | BE Dev | Todo | Await UX Lead adoption report |
| T004 | FE Dev: adopt Replit components | FE Dev | Todo | Await adoption report |
| T005 | QA: Integration and Chaos suites | QA Engineer | Todo | Await build completion |
EOF

# ── 9. Initialize Git ─────────────────────────────────────────
echo "[7/13] Initializing Git..."
git init
git add .
git commit -m "Initial commit: Hammerfall v4.1 scaffold — $PROJECT_NAME"

# ── 10. Create GitHub Repo and Push Main ─────────────────────
echo "[8/13] Creating GitHub repository: Hammerfall-$PROJECT_NAME..."
gh repo create "Hammerfall-$PROJECT_NAME" --private --source=. --remote=origin --push

# ── 11. Create Develop Branch ────────────────────────────────
echo "[9/13] Creating develop branch..."
git checkout -b develop
git push -u origin develop

# ── 12. Create Replit Branch ─────────────────────────────────
echo "[10/13] Creating replit/ui-v1 branch..."
git checkout -b replit/ui-v1
git push -u origin replit/ui-v1
git checkout develop

# ── 13. Supabase — Full Auto Setup ───────────────────────────
echo "[11/13] Setting up Supabase..."

# Initialize local config folder
supabase init

# Verify CLI auth before cloud operations
if ! supabase projects list > /dev/null 2>&1; then
  echo ""
  echo "  ⚠️  SUPABASE AUTH REQUIRED — run: supabase login"
  echo "  Then re-run bootstrap."
  echo ""
  exit 1
fi

# Create cloud project under Hammerfall org
echo "  -> Creating Supabase cloud project: Hammerfall-$PROJECT_NAME"
supabase projects create "Hammerfall-$PROJECT_NAME" \
  --org-id "$SUPABASE_ORG_ID" \
  --db-password "$DB_PASSWORD" \
  --region "$SUPABASE_REGION"

# Wait for provisioning
echo "  -> Waiting for project to provision (10s)..."
sleep 10

# Retrieve project ref
PROJECT_REF=$(supabase projects list \
  | grep "Hammerfall-$PROJECT_NAME" \
  | awk '{print $1}')

if [ -z "$PROJECT_REF" ]; then
  echo "  WARNING: Could not retrieve project ref automatically."
  echo "  Get it from supabase.com/dashboard and add to .env.local manually."
else
  SUPABASE_URL="https://$PROJECT_REF.supabase.co"

  # Try new publishable key format first, fall back to legacy anon key
  SUPABASE_ANON_KEY=$(supabase projects api-keys --project-ref "$PROJECT_REF" \
    | grep -E "publishable|anon" | head -1 | awk '{print $NF}')

  # Fallback warning if key still blank (new key format may require dashboard reveal)
  if [ -z "$SUPABASE_ANON_KEY" ]; then
    echo ""
    echo "  ⚠️  Could not retrieve publishable/anon key automatically."
    echo "  Supabase new key format requires manual reveal."
    echo "  Get it from: supabase.com/dashboard/project/$PROJECT_REF/settings/api-keys"
    echo "  Then update .env.local: NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key-here"
    echo ""
    SUPABASE_ANON_KEY="REPLACE_WITH_KEY_FROM_SUPABASE_DASHBOARD"
  fi

  # Write credentials to .env.local
  cat > .env.local << EOF
NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
# DB password (for direct database access only — never expose publicly)
SUPABASE_DB_PASSWORD=$DB_PASSWORD
EOF

  # Add .env.local to .gitignore
  if ! grep -q ".env.local" .gitignore 2>/dev/null; then
    echo ".env.local" >> .gitignore
  fi

  echo "  -> Cloud project created: $SUPABASE_URL"
  echo "  -> Credentials written to .env.local"
  if [ "$SUPABASE_ANON_KEY" = "REPLACE_WITH_KEY_FROM_SUPABASE_DASHBOARD" ]; then
    echo "  -> ⚠️  Anon key placeholder — update .env.local manually before building"
  fi
fi

# ── 14. Install Node Dependencies ────────────────────────────
echo "[12/13] Installing Node dependencies..."
if [ -f "package.json" ]; then
  npm install
else
  echo "  -> No package.json found. Skipping npm install."
fi

# ── 15. Generate Initial SITREP ──────────────────────────────
echo "[13/13] Generating initial SITREP..."
cat > "SITREPs/$(date +%Y-%m-%d)_SITREP.md" << EOF
# SITREP — $PROJECT_NAME
**Date:** $(date +%Y-%m-%d)
**Status:** LAUNCHED
**Author:** Project Helm

---

## Environment State

- [x] GitHub Repository Created: Hammerfall-$PROJECT_NAME (private)
- [x] Branches: main, develop, replit/ui-v1
- [x] Project Helm present at agents/helm/
- [x] Local Supabase initialized
- [x] Supabase cloud project created under Hammerfall org
- [x] Credentials written to .env.local
- [x] REPLIT_INSTRUCTIONS.md in place
- [x] SITREPs/TASKS.md created
- [ ] Specs confirmed complete (check specs/ready/)
- [ ] Vercel linked (triggers on first merge to main)

---

## PR-First Rule — Mandatory

No branch absorbs another branch's work without a merged PR.

- replit/ui-v1 → PR → develop (Antigravity never pulls directly from replit/ui-v1)
- Feature branches → PR → develop
- develop → PR → main (Maxwell approval required)

Violating this rule causes merge conflicts. There are no exceptions.

---

## Next Steps

1. Connect Replit to this repo (defaults to main — read REPLIT_INSTRUCTIONS.md)
2. Open Antigravity on develop branch
3. Run Claude Code: "Build the project. Follow PROJECT_RULES.md. Use the agent system."
4. Project Helm monitors PRs and SITREPs from agents/helm/

---

## Active Tasks

See SITREPs/TASKS.md for full task board.
EOF

git add .
git commit -m "Launch: initial SITREP, Project Helm clone, TASKS.md — $PROJECT_NAME"
git push origin develop

# ── 16. Update active-projects.md in hammerfall-solutions ────
echo "Updating active-projects.md in hammerfall-solutions..."
cd "$HAMMERFALL_DIR"

cat >> active-projects.md << EOF
| $PROJECT_NAME | $PROJECT_DIR | $(date +%Y-%m-%d) | active |
EOF

git add active-projects.md
git commit -m "chore: add $PROJECT_NAME to active-projects.md"
git push origin main

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "LAUNCH COMPLETE: Hammerfall-$PROJECT_NAME"
echo "============================================"
echo ""
echo "Repo:     Hammerfall-$PROJECT_NAME (private)"
echo "Branches: main | develop (current) | replit/ui-v1"
echo "Helm:     agents/helm/helm_prompt.md"
echo "Tasks:    SITREPs/TASKS.md"
echo "Supabase: credentials in .env.local"
echo ""
echo "Next: connect Replit to replit/ui-v1, then open Antigravity on develop."
