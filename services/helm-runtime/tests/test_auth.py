"""Tests for the static bearer-token auth dependency (T0.A8).

Two layers:

1. Unit tests on `require_token` directly — exercise the dependency function
   with monkeypatched env, no FastAPI app needed.
2. Integration tests against a minimal FastAPI app that mounts a single
   protected route and `/health` (exempt). Avoids spinning up the real
   helm-runtime app, which needs Supabase/Anthropic env to start.
"""

from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import ENV_VAR, require_token

VALID_TOKEN = "test-token-abcdef0123456789"


# ---------------------------------------------------------------------------
# Unit tests — call require_token() directly. Convert HTTPException to status.
# ---------------------------------------------------------------------------


def _check(authorization: str | None) -> int:
    """Run the dependency, return the HTTP status it would produce.
    200 means it accepted the call (returned None)."""
    from fastapi import HTTPException

    try:
        require_token(authorization=authorization)
        return 200
    except HTTPException as e:
        return e.status_code


def test_unit_missing_env_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert _check("Bearer anything") == 500


def test_unit_no_header_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, VALID_TOKEN)
    assert _check(None) == 401


def test_unit_malformed_header_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, VALID_TOKEN)
    assert _check("Basic abc123") == 401
    assert _check("Bear " + VALID_TOKEN) == 401  # typo'd scheme
    assert _check(VALID_TOKEN) == 401  # missing scheme


def test_unit_wrong_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, VALID_TOKEN)
    assert _check("Bearer wrong-token") == 401


def test_unit_correct_token_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, VALID_TOKEN)
    assert _check(f"Bearer {VALID_TOKEN}") == 200


# ---------------------------------------------------------------------------
# Integration tests — minimal FastAPI app exercising the 401/200 paths
# end-to-end through the request pipeline (header parsing, response codes,
# WWW-Authenticate header).
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv(ENV_VAR, VALID_TOKEN)

    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_token)])
    def protected() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as c:
        yield c


def test_integration_health_open_no_auth(client: TestClient) -> None:
    """/health must remain exempt (Docker/Render healthchecks)."""
    r = client.get("/health")
    assert r.status_code == 200


def test_integration_protected_without_token_returns_401(client: TestClient) -> None:
    r = client.get("/protected")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_integration_protected_with_wrong_token_returns_401(client: TestClient) -> None:
    r = client.get("/protected", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_integration_protected_with_correct_token_returns_200(client: TestClient) -> None:
    r = client.get("/protected", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
