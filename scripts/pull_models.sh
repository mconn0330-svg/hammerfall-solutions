#!/bin/bash
# =============================================================
# Helm Runtime Service — Ollama Model Pre-Pull
#
# Pulls every Qwen model required by the helm-runtime stack into
# the Ollama container's persistent volume. One-time operation —
# subsequent docker-compose up does not re-pull (volume persists).
#
# Prerequisite:
#   The hammerfall-solutions docker-compose stack must be running.
#   Run: docker-compose up -d
#
# Usage:
#   bash scripts/pull_models.sh
#
# Total disk: ~17 GB (qwen3:4b ~2.6 GB, qwen3:8b ~5.2 GB, qwen3:14b ~9 GB).
# Time: ~10–30 minutes on a typical home connection.
#
# Models tracked here must match the agent assignments in
# services/helm-runtime/config.yaml. If model versions change there,
# update this list to keep /health green after a clean compose down -v.
# =============================================================

set -euo pipefail

CONTAINER="hammerfall-solutions-ollama-1"

if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER}$"; then
  echo "Error: container '${CONTAINER}' is not running."
  echo "Start the stack first: docker-compose up -d"
  exit 1
fi

# Three unique models. qwen3:14b serves both Archivist and Contemplator.
MODELS=("qwen3:4b" "qwen3:8b" "qwen3:14b")

for model in "${MODELS[@]}"; do
  echo "==> Pulling ${model}"
  docker exec "${CONTAINER}" ollama pull "${model}"
done

echo
echo "==> All models pulled."
echo "    Verify: curl http://localhost:8000/health"
