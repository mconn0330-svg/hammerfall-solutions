"""Tests for memory.prompt — PromptManager load / push / pull + refuse-to-boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from memory.prompt import PromptManager, PromptUnavailable

# ─── Test doubles ───────────────────────────────────────────────────────────


class _StubSupabase:
    """Minimal _SupabaseLike that records calls and returns canned data.

    Tests configure `select_returns` per-instance; insert/patch always succeed
    and append to the calls list.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        # select_returns: list of return values, popped in FIFO order
        self.select_returns: list[list[dict[str, Any]]] = []
        self.select_raises: Exception | None = None
        self.insert_raises: Exception | None = None
        self.patch_raises: Exception | None = None

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls.append(("select", table, params))
        if self.select_raises is not None:
            raise self.select_raises
        if self.select_returns:
            return self.select_returns.pop(0)
        return []

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("insert", table, payload))
        if self.insert_raises is not None:
            raise self.insert_raises
        return payload

    async def patch(
        self, table: str, filters: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        self.calls.append(("patch", table, {"filters": filters, "payload": payload}))
        if self.patch_raises is not None:
            raise self.patch_raises
        return [payload]


# ─── load() ─────────────────────────────────────────────────────────────────


async def test_load_returns_supabase_content_when_available() -> None:
    sb = _StubSupabase()
    sb.select_returns = [[{"content": "PROMPT FROM SUPABASE", "version": 3}]]
    pm = PromptManager(sb)

    result = await pm.load("helm_prime")
    assert result == "PROMPT FROM SUPABASE"
    # Supabase was queried with the right filters
    _, table, params = sb.calls[0]
    assert table == "helm_prompts"
    assert params["agent_role"] == "eq.helm_prime"
    assert params["active"] == "eq.true"


async def test_load_falls_back_to_file_when_supabase_empty(tmp_path: Path) -> None:
    """Supabase returned [] (no row for this role) — file fallback fires."""
    fallback = tmp_path / "helm_prime.md"
    fallback.write_text("PROMPT FROM FILE", encoding="utf-8")

    sb = _StubSupabase()
    sb.select_returns = [[]]  # empty → fall through
    pm = PromptManager(sb, fallback_dir=tmp_path)

    result = await pm.load("helm_prime")
    assert result == "PROMPT FROM FILE"


async def test_load_falls_back_to_file_when_supabase_raises(tmp_path: Path) -> None:
    """Supabase unreachable (network error) — file fallback fires."""
    fallback = tmp_path / "helm_prime.md"
    fallback.write_text("PROMPT FROM FILE", encoding="utf-8")

    sb = _StubSupabase()
    sb.select_raises = ConnectionError("supabase down")
    pm = PromptManager(sb, fallback_dir=tmp_path)

    result = await pm.load("helm_prime")
    assert result == "PROMPT FROM FILE"


async def test_load_explicit_fallback_path_overrides_dir(tmp_path: Path) -> None:
    """Per-call fallback_path wins over fallback_dir."""
    explicit = tmp_path / "explicit.md"
    explicit.write_text("EXPLICIT PATH WINS", encoding="utf-8")
    in_dir = tmp_path / "helm_prime.md"
    in_dir.write_text("DIR-RESOLVED LOSES", encoding="utf-8")

    sb = _StubSupabase()
    sb.select_returns = [[]]
    pm = PromptManager(sb, fallback_dir=tmp_path)

    result = await pm.load("helm_prime", fallback_path=explicit)
    assert result == "EXPLICIT PATH WINS"


async def test_load_raises_prompt_unavailable_on_dual_failure() -> None:
    """Both paths fail → refuse to serve. This is the load-bearing assertion
    behind the runtime's refuse-to-boot behavior."""
    sb = _StubSupabase()
    sb.select_raises = ConnectionError("supabase down")
    pm = PromptManager(sb)  # no fallback_dir

    with pytest.raises(PromptUnavailable):
        await pm.load("helm_prime")


async def test_load_raises_when_supabase_empty_and_no_file(tmp_path: Path) -> None:
    """Supabase empty + file missing → PromptUnavailable. No silent empty-string fallback."""
    sb = _StubSupabase()
    sb.select_returns = [[]]
    pm = PromptManager(sb, fallback_dir=tmp_path)  # tmp_path empty, no helm_prime.md

    with pytest.raises(PromptUnavailable):
        await pm.load("helm_prime")


async def test_load_raises_when_no_fallback_configured() -> None:
    """No fallback_dir AND no per-call path → Supabase failure raises."""
    sb = _StubSupabase()
    sb.select_returns = [[]]
    pm = PromptManager(sb)  # no fallback_dir

    with pytest.raises(PromptUnavailable):
        await pm.load("helm_prime")


# ─── push() ─────────────────────────────────────────────────────────────────


async def test_push_writes_version_1_when_no_existing_rows() -> None:
    sb = _StubSupabase()
    sb.select_returns = [[]]  # max-version query returns nothing
    pm = PromptManager(sb)

    version = await pm.push("helm_prime", "v1 content", pushed_by="test")
    assert version == 1
    # Insert call shape
    insert_calls = [c for c in sb.calls if c[0] == "insert"]
    assert len(insert_calls) == 1
    _, _, payload = insert_calls[0]
    assert payload["agent_role"] == "helm_prime"
    assert payload["version"] == 1
    assert payload["content"] == "v1 content"
    assert payload["active"] is True
    assert payload["pushed_by"] == "test"


async def test_push_increments_version_when_existing_rows() -> None:
    sb = _StubSupabase()
    sb.select_returns = [[{"version": 4}]]  # latest version is 4
    pm = PromptManager(sb)

    version = await pm.push("helm_prime", "v5 content")
    assert version == 5


async def test_push_deactivates_previous_active_then_inserts() -> None:
    """The deactivate PATCH happens BEFORE the insert — partial-failure
    semantics: insert failure leaves no active row, but next push can recover."""
    sb = _StubSupabase()
    sb.select_returns = [[{"version": 2}]]
    pm = PromptManager(sb)

    await pm.push("helm_prime", "v3 content")

    # Order: select(max version), patch(deactivate), insert(new active)
    op_sequence = [c[0] for c in sb.calls]
    assert op_sequence == ["select", "patch", "insert"]

    # Patch flagged previous as inactive
    _, _, patch_args = sb.calls[1]
    assert patch_args["payload"] == {"active": False}
    assert patch_args["filters"] == {"agent_role": "helm_prime", "active": "true"}


async def test_push_records_optional_notes_field() -> None:
    sb = _StubSupabase()
    pm = PromptManager(sb)

    await pm.push("helm_prime", "content", notes="Fix a typo")
    insert_payload = next(c for c in sb.calls if c[0] == "insert")[2]
    assert insert_payload["notes"] == "Fix a typo"


async def test_push_omits_notes_when_not_provided() -> None:
    sb = _StubSupabase()
    pm = PromptManager(sb)

    await pm.push("helm_prime", "content")
    insert_payload = next(c for c in sb.calls if c[0] == "insert")[2]
    assert "notes" not in insert_payload


# ─── pull() ─────────────────────────────────────────────────────────────────


async def test_pull_writes_active_content_to_target_path(tmp_path: Path) -> None:
    sb = _StubSupabase()
    sb.select_returns = [[{"content": "ACTIVE PROMPT", "version": 7}]]
    pm = PromptManager(sb)
    target = tmp_path / "out" / "helm_prime.md"

    version = await pm.pull("helm_prime", target)
    assert version == 7
    assert target.read_text(encoding="utf-8") == "ACTIVE PROMPT"


async def test_pull_creates_parent_directories(tmp_path: Path) -> None:
    sb = _StubSupabase()
    sb.select_returns = [[{"content": "x", "version": 1}]]
    pm = PromptManager(sb)
    target = tmp_path / "deeply" / "nested" / "path" / "prime.md"

    await pm.pull("helm_prime", target)
    assert target.exists()


async def test_pull_is_atomic_via_os_replace(tmp_path: Path) -> None:
    """The temp file used during pull is gone after the call — write went
    straight through os.replace, not left behind as a stale .tmp."""
    sb = _StubSupabase()
    sb.select_returns = [[{"content": "x", "version": 1}]]
    pm = PromptManager(sb)
    target = tmp_path / "prime.md"

    await pm.pull("helm_prime", target)

    # Target exists, no .tmp leftovers
    assert target.exists()
    leftovers = list(tmp_path.glob(".prime.md.*.tmp"))
    assert leftovers == []


async def test_pull_overwrites_existing_target(tmp_path: Path) -> None:
    """os.replace handles overwrite cross-platform — Windows-safe."""
    target = tmp_path / "prime.md"
    target.write_text("OLD CONTENT", encoding="utf-8")

    sb = _StubSupabase()
    sb.select_returns = [[{"content": "NEW CONTENT", "version": 2}]]
    pm = PromptManager(sb)

    await pm.pull("helm_prime", target)
    assert target.read_text(encoding="utf-8") == "NEW CONTENT"


async def test_pull_raises_when_no_active_row(tmp_path: Path) -> None:
    """Pull is Supabase → file. If Supabase has nothing, raise — don't
    silently leave the file in its prior state."""
    sb = _StubSupabase()
    sb.select_returns = [[]]
    pm = PromptManager(sb)
    target = tmp_path / "prime.md"

    with pytest.raises(PromptUnavailable):
        await pm.pull("helm_prime", target)
