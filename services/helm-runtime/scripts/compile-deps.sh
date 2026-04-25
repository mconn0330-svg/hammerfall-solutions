#!/usr/bin/env bash
# T0.A7 — Regenerate helm-runtime lockfiles inside a Linux container that
# matches CI's Python version and OS, so local + CI produce identical output.
#
# Why this exists: pip-compile run on Windows includes platform-conditional
# deps (colorama for click/tqdm) that Linux doesn't need. Running pip-compile
# in the runtime base image (python:3.12.4-slim-bookworm) avoids the drift.
#
# Usage:
#   bash services/helm-runtime/scripts/compile-deps.sh
#
# Run after editing requirements.in or requirements-dev.in.

set -euo pipefail

# Resolve repo paths so this works from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# On Git Bash for Windows, $PWD-style paths get mangled by MSYS path
# translation when passed to docker. -w /work is the in-container path;
# `pwd -W` (Git Bash) returns the Windows path docker can mount; on
# Linux/macOS, plain $PWD works.
if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
  HOST_DIR="$(cd "$RUNTIME_DIR" && pwd -W)"
  export MSYS_NO_PATHCONV=1
else
  HOST_DIR="$RUNTIME_DIR"
fi

echo "Regenerating lockfiles in python:3.12.4-slim-bookworm (matches CI + Dockerfile)..."

docker run --rm \
  -v "$HOST_DIR:/work" \
  -w /work \
  python:3.12.4-slim-bookworm \
  sh -c "
    pip install pip-tools==7.5.3 --quiet &&
    pip-compile --generate-hashes --strip-extras --quiet \
      -o requirements.txt requirements.in &&
    pip-compile --generate-hashes --strip-extras --allow-unsafe --quiet \
      --constraint requirements.txt \
      -o requirements-dev.txt requirements-dev.in
  "

echo "Done. Commit requirements.txt + requirements-dev.txt alongside the .in changes."
