# T0.A7 — Production-shaped runtime image.
# Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A7
# Arch note: docs/stage1/arch_notes/T0.A7_deployment_hardening.md
#
# Multi-stage:
#   builder  — installs hashed deps into a wheelhouse
#   runtime  — slim final image, non-root user (helm:1000), healthcheck
#
# Base image is pinned per architect: python:3.12.4-slim-bookworm.
# Track patch-line bumps for security; do not float to 3.13 without coordination.

# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12.4

# ---- Builder stage --------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

WORKDIR /build

# Hashed lockfile — pip enforces hashes automatically when present.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# ---- Runtime stage --------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

# Non-root user — created BEFORE COPY so file ownership is correct.
# UID 1000 matches docker-compose's expected host UID for bind mounts.
RUN groupadd --system --gid 1000 helm \
 && useradd --system --uid 1000 --gid helm --create-home --home-dir /home/helm helm

WORKDIR /app

# Install pre-built wheels (offline — no network in runtime layer).
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels requirements.txt

# Service code — owned by helm so non-root can read.
COPY --chown=helm:helm . .

# Drop to non-root for runtime.
USER helm

EXPOSE 8000

# Healthcheck via stdlib urllib — no curl in slim base image.
# Calls /health (GET); 200 → healthy, anything else → unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health', timeout=5); sys.exit(0 if r.status == 200 else 1)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
