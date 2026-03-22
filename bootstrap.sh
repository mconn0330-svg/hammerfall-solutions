#!/bin/bash

# =============================================================
# HAMMERFALL SOLUTIONS — AUTONOMOUS PROJECT BOOTSTRAPPER v3
# Executed by: Helm (Technical Director)
# =============================================================

set -e

# 1. Parameter Validation
PROJECT_NAME=$1
if [ -z "$PROJECT_NAME" ]; then
  echo "ERROR: Project codename required."
  echo "Usage: ./bootstrap.sh [codename]"
  exit 1
fi

PROJECT_DIR="../$PROJECT_NAME"
echo "INITIATING LAUNCH SEQUENCE FOR: $PROJECT_NAME"

# 2. Scaffold from Master Template
echo "Scaffolding from Master Template..."
cp -r project_structure_template $PROJECT_DIR
cd $PROJECT_DIR

# 3. Inject Project Rules
echo "Injecting PROJECT_RULES.md..."
if [ ! -f "PROJECT_RULES.md" ]; then
  cp ../hammerfall-solutions/project_structure_template/Project_Rules ./PROJECT_RULES.md \
    2>/dev/null || echo "Warning: Project_Rules not found in master repo."
fi

# 4. Inject Replit Instructions
echo "Injecting REPLIT_INSTRUCTIONS.md..."
cp ../hammerfall-solutions/project_structure_template/REPLIT_INSTRUCTIONS.md \
  ./REPLIT_INSTRUCTIONS.md 2>/dev/null \
  || echo "Warning: REPLIT_INSTRUCTIONS.md not found in master repo."

# 5. Inject Staged Specs
echo "Checking for staged specs..."
STAGING_DIR="../hammerfall-solutions/staging_area/$PROJECT_NAME"
if [ -d "$STAGING_DIR" ] && [ "$(ls -A $STAGING_DIR 2>/dev/null)" ]; then
  echo "   -> Found specs for $PROJECT_NAME. Moving to specs/ready/..."
  mkdir -p specs/ready
  cp $STAGING_DIR/* ./specs/ready/
  echo "   -> Specs injected successfully."
else
  echo "   -> No staged specs found for $PROJECT_NAME."
fi

# 6. Initialize Git
echo "Initializing Git..."
git init
git add .
git commit -m "Initial commit: Hammerfall v3 scaffold"

# 7. Create GitHub repo and push main
echo "Creating GitHub repository..."
gh repo create "Hammerfall-$PROJECT_NAME" --private --source=. --remote=origin --push

# 8. Create develop branch
echo "Creating develop branch..."
git checkout -b develop
git push -u origin develop

# 9. Create replit/ui-v1 branch
echo "Creating replit/ui-v1 branch..."
git checkout -b replit/ui-v1
git push -u origin replit/ui-v1

# 10. Return to develop as default working branch
echo "Setting develop as default working branch..."
git checkout develop

# 11. Initialize Local Supabase
echo "Initializing local Supabase..."
supabase init

# 12. Install Node dependencies
echo "Installing Node dependencies..."
if [ -f "package.json" ]; then
  npm install
fi

# 13. Generate initial SITREP
echo "Generating initial SITREP..."
mkdir -p SITREPs
cat <<EOF > SITREPs/$(date +%Y-%m-%d)_SITREP.md
# SITREP — $PROJECT_NAME
**Date:** $(date +%Y-%m-%d)
**Status:** LAUNCHED

## Environment State
- [x] GitHub Repository Created (Hammerfall-$PROJECT_NAME)
- [x] Branches: main, develop, replit/ui-v1
- [x] Local Supabase Initialized
- [x] Specs injected from staging
- [x] REPLIT_INSTRUCTIONS.md in place
- [ ] Vercel linked (pending first merge to main)
- [ ] GitHub secrets configured

## Next Steps
1. Connect Replit to this repo on branch replit/ui-v1
2. Run Replit agent: "Read REPLIT_INSTRUCTIONS.md and specs/ready/"
3. Open Antigravity, connect to this repo on develop
4. Run claude and say: "Build the project. Follow CLAUDE.md."
EOF

git add .
git commit -m "Add initial SITREP"
git push origin develop

# 14. Done
echo "============================================"
echo "LAUNCH COMPLETE: Hammerfall-$PROJECT_NAME"
echo "============================================"
echo ""
echo "Branches created:"
echo "  main          — production (auto-deploys to Vercel on merge)"
echo "  develop       — active development (current)"
echo "  replit/ui-v1  — Replit UI prototype"
echo ""
echo "Next: connect Replit to replit/ui-v1, then open Antigravity on develop."
