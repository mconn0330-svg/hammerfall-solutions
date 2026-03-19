#!/bin/bash

# ==============================================================================
# HAMMERFALL SOLUTIONS - AUTONOMOUS PROJECT BOOTSTRAPPER
# Executed by: Helm (Technical Director)
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# 1. Parameter Validation
PROJECT_NAME=$1
if [ -z "$PROJECT_NAME" ]; then
  echo "❌ ERROR: Project codename required."
  echo "Usage: ./bootstrap.sh [codename]"
  exit 1
fi

PROJECT_DIR="../$PROJECT_NAME"
echo "🚀 INITIATING LAUNCH SEQUENCE FOR: $PROJECT_NAME"

# 2. Clone the Master Template
echo "📂 Scaffolding local directory from Master Template..."
# Assuming 'project_structure_template' is your template folder in the root
cp -r project_structure_template $PROJECT_DIR
cd $PROJECT_DIR

# 3. Inject Local Project Rules
echo "📜 Injecting PROJECT_RULES.md..."
if [ ! -f "PROJECT_RULES.md" ]; then
    cp ../hammerfall-solutions/management/PROJECT_RULES.md ./PROJECT_RULES.md 2>/dev/null || echo "⚠️ Warning: PROJECT_RULES.md not found in master repo."
fi

# 4. Initialize Local Git & GitHub Repository
echo "🐙 Initializing Git and GitHub Repository..."
git init
git add .
git commit -m "Initial commit: Hammerfall AAO Template Scaffold"

# Use GitHub CLI to create a private repo and push the initial code
gh repo create "Hammerfall-$PROJECT_NAME" --private --source=. --remote=origin --push

# 5. Infrastructure: Local-First Supabase
echo "🗄️ Initializing Local Supabase Environment..."
supabase init

# 6. Infrastructure: App Setup
echo "📦 Installing Node Dependencies..."
if [ -f "package.json" ]; then
    npm install
fi

# 7. Create Initial SITREP for Helm
echo "📝 Generating initial SITREP.md..."
cat <<EOF > SITREP.md
# Situation Report (SITREP) - $PROJECT_NAME
**Date:** $(date +%Y-%m-%d)
**Status:** LAUNCHED

## Environment State
- [x] GitHub Repository Created (Hammerfall-$PROJECT_NAME)
- [x] Local Supabase Initialized
- [x] Node Dependencies Installed
- [ ] Vercel/EAS Cloud Linked (Pending Friday Merge)

## Next Steps for Project Agent
1. Review Muse's UI Blueprints.
2. Review Scout's JTBD PRD.
3. Begin local development on the \`develop\` branch.
EOF

git add SITREP.md
git commit -m "Add initial SITREP.md"
git branch -M develop
git push -u origin develop

# 8. Handoff to Helm
echo "=============================================================================="
echo "✅ LAUNCH COMPLETE: $PROJECT_NAME"
echo "=============================================================================="
echo "HELM DIRECTIVE: Run 'code .' or use Antigravity CLI to open this workspace."
echo "HELM DIRECTIVE: Proceed to Slack to create channel and assign the Doer Agent."