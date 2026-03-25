#!/bin/bash
# =============================================================
# HAMMERFALL SOLUTIONS — AUTONOMOUS PROJECT BOOTSTRAPPER v4
# Executed by: Helm (Technical Director)
# Architecture: IDE-First, Repo-Brain, Project Helm Clone
# =============================================================
set -e

# ── 1. Parameter Validation ───────────────────────────────────
PROJECT_NAME=$1
if [ -z "$PROJECT_NAME" ]; then
  echo "ERROR: Project codename required."
  echo "Usage: ./bootstrap.sh [codename]"
  exit 1
fi

HAMMERFALL_DIR="$(pwd)"
PROJECT_DIR="../Hammerfall-$PROJECT_NAME"

echo "============================================"
echo "INITIATING LAUNCH SEQUENCE FOR: $PROJECT_NAME"
echo "============================================"

# ── 2. Scaffold from Master Template ─────────────────────────
echo "[1/13] Scaffolding from project_structure_template..."
cp -r "$HAMMERFALL_DIR/project_structure_template" "$PROJECT_DIR"
cd "$PROJECT_DIR"

# ── 3. Inject Project Helm Clone ─────────────────────────────
echo "[2/13] Cloning Project Helm into repo..."
mkdir -p agents/helm/memory/LongTerm
cp "$HAMMERFALL_DIR/project_structure_template/agents/helm/helm_prompt.md" \
   agents/helm/helm_prompt.md

# Replace [PROJECT_NAME] placeholder with actual codename
sed -i "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" agents/helm/helm_prompt.md

# Scaffold blank memory files with headers
cat > agents/helm/memory/ShortTerm_Scratchpad.md << EOF
# Project Helm — ShortTerm Scratchpad
**Project:** $PROJECT_NAME
**Last flushed:** $(date +%Y-%m-%d)

Active working memory for the current session.
Transfer relevant entries to BEHAVIORAL_PROFILE.md at session end, then clear this file.
EOF

cat > agents/helm/memory/BEHAVIORAL_PROFILE.md << EOF
# Project Helm — Behavioral Profile
**Project:** $PROJECT_NAME
**Created:** $(date +%Y-%m-%d)

Permanent record of architectural decisions, Maxwell preferences, and patterns learned.
Document the decision AND the reasoning — never just the outcome.
Prefix significant milestone entries with [SYNC-READY] for Core Helm sync detection.
EOF

cat > agents/helm/memory/LongTerm/MEMORY_INDEX.md << EOF
# Project Helm — Long Term Memory Index
**Project:** $PROJECT_NAME

One-line entry per archived event. Format: YYYY-MM-DD | [topic] | [brief summary]
EOF

# ── 4. Inject Project Rules ───────────────────────────────────
echo "[3/13] Injecting PROJECT_RULES.md..."
# Exactly one Project_Rules file — no duplicates
if [ -f "Project_Rules" ]; then
  mv Project_Rules PROJECT_RULES.md
elif [ ! -f "PROJECT_RULES.md" ]; then
  echo "  WARNING: No Project_Rules file found in template. Skipping."
fi

# ── 5. Inject Replit Instructions ─────────────────────────────
echo "[4/13] Injecting REPLIT_INSTRUCTIONS.md..."
if [ ! -f "REPLIT_INSTRUCTIONS.md" ]; then
  cp "$HAMMERFALL_DIR/project_structure_template/REPLIT_INSTRUCTIONS.md" . \
  2>/dev/null || echo "  WARNING: REPLIT_INSTRUCTIONS.md not found in master repo."
fi

# ── 6. Inject Staged Specs ────────────────────────────────────
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

# ── 7. Create SITREPs folder and TASKS.md ────────────────────
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

# ── 8. Initialize Git ─────────────────────────────────────────
echo "[7/13] Initializing Git..."
git init
git add .
git commit -m "Initial commit: Hammerfall v4 scaffold — $PROJECT_NAME"

# ── 9. Create GitHub Repo and Push Main ───────────────────────
echo "[8/13] Creating GitHub repository: Hammerfall-$PROJECT_NAME..."
gh repo create "Hammerfall-$PROJECT_NAME" --private --source=. --remote=origin --push

# ── 10. Create Develop Branch ─────────────────────────────────
echo "[9/13] Creating develop branch..."
git checkout -b develop
git push -u origin develop

# ── 11. Create Replit Branch ──────────────────────────────────
echo "[10/13] Creating replit/ui-v1 branch..."
git checkout -b replit/ui-v1
git push -u origin replit/ui-v1

# Return to develop as default working branch
git checkout develop

# ── 12. Initialize Local Supabase ─────────────────────────────
echo "[11/13] Initializing local Supabase..."
echo ""
echo "  ⚠️  SUPABASE AUTH REMINDER ⚠️"
echo "  If this is a new project, ensure you are logged in:"
echo "  Run: supabase login"
echo "  Then create a new project at: https://supabase.com/dashboard"
echo "  Paste the project URL and anon key into .env.local when prompted."
echo ""
supabase init

# ── 13. Install Node Dependencies ────────────────────────────
echo "[12/13] Installing Node dependencies..."
if [ -f "package.json" ]; then
  npm install
else
  echo "  -> No package.json found. Skipping npm install."
fi

# ── 14. Generate Initial SITREP ──────────────────────────────
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
- [x] REPLIT_INSTRUCTIONS.md in place
- [x] SITREPs/TASKS.md created
- [ ] Specs injected from staging (check specs/ready/)
- [ ] Supabase project created and credentials configured
- [ ] Vercel linked (pending first merge to main)

---

## PR-First Rule — Mandatory

No branch absorbs another branch's work without a merged PR.

- replit/ui-v1 → PR → develop (Antigravity never pulls directly from replit/ui-v1)
- Feature branches → PR → develop
- develop → PR → main (Maxwell approval required)

Violating this rule causes merge conflicts. There are no exceptions.

---

## Next Steps

1. Connect Replit to this repo (it will default to main — read REPLIT_INSTRUCTIONS.md)
2. Open Antigravity on develop branch
3. Run Claude Code: "Build the project. Follow CLAUDE.md. Use the agent system."
4. Project Helm monitors PRs and SITREPs from agents/helm/

---

## Active Tasks

See SITREPs/TASKS.md for full task board.
EOF

git add .
git commit -m "Launch: initial SITREP, Project Helm clone, TASKS.md — $PROJECT_NAME"
git push origin develop

# ── 15. Update active-projects.md in hammerfall-solutions ─────
echo "Updating active-projects.md in hammerfall-solutions..."
cd "$HAMMERFALL_DIR"

# Append new project entry to active-projects.md
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
echo ""
echo "⚠️  BEFORE BUILDING:"
echo "   1. Run 'supabase login' if not already authenticated"
echo "   2. Create Supabase project at https://supabase.com/dashboard"
echo "   3. Add credentials to .env.local"
echo ""
echo "Next: connect Replit to replit/ui-v1, then open Antigravity on develop."
