"""
auth.py — Static bearer-token gate for the helm-runtime service.

T0.A8 — gates `/invoke/*` and `/config/*`. `/health` is intentionally exempt
so Docker/Render healthchecks (and any future ops monitor) can probe without
provisioning a token.

Threat model at T1: "noise on the box." A drive-by curl from any process on
the host should not be able to drain Anthropic Pro Max quota or external API
budget. Static bearer is the lowest-cost auth that's actually a boundary —
not user identity, not session state, just attribution.

Token comes from `HELM_API_TOKEN` env var. Generate one with:

    openssl rand -hex 32

Manual rotation procedure: docs/runbooks/0001-api-token-rotation.md.

Usage on a route:

    from auth import require_token

    @app.post("/invoke/{role}", dependencies=[Depends(require_token)])
    async def invoke(...): ...
"""

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

ENV_VAR = "HELM_API_TOKEN"


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """FastAPI dependency that enforces a static bearer token.

    - Missing `HELM_API_TOKEN` env var → 500 (server misconfigured, not the
      caller's fault). T0.A12 CI smoke should catch this before deploy.
    - Missing or malformed `Authorization` header → 401.
    - Non-matching token → 401 (constant-time compare to avoid timing leaks).
    """
    expected = os.environ.get(ENV_VAR)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server misconfigured: {ENV_VAR} not set.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len("Bearer ") :]
    if not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
