"""Prompt management — Supabase as source of truth, file as fallback.

T0.B5. Replaces the mount-the-file-and-restart pattern from helm_prime
where the on-disk `helm_prompt.md` was the canonical source. Now:

  - Supabase `helm_prompts` table is the source of truth (push promotes a
    file-version to active; load reads active row by agent role).
  - The on-disk file is the boot-time fallback — if Supabase is unreachable
    at startup, the runtime can still serve from the local prompt file.
  - If BOTH are unreachable, the runtime refuses to boot. Fail-loud beats
    fail-silent with stale data.

PromptManager is operator infrastructure — push and pull are explicit
operator actions. Reads use the same Supabase client as everything else
on the read side. Writes go directly through ReadClient (not through
MemoryClient/Outbox) — push is an explicit operator action; outbox-style
queueing on a config write would mask operator-visible failures.

Push semantics:
  - Reads the file content (or accepts raw content as an argument).
  - Inserts a new row with version = max(existing) + 1, active = true.
  - Deactivates the previous active row for that agent_role.
  - Both writes happen in sequence; partial failure leaves no active
    row (next push retries deactivation as part of its own transaction).

Pull semantics:
  - Reads active row by agent_role.
  - Writes content to target_path atomically via os.replace.
  - Returns the version pulled.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Protocol

from observability import get_logger

logger = get_logger("helm.memory.prompt")


# ─── Errors ─────────────────────────────────────────────────────────────────


class PromptManagerError(Exception):
    """Base error from PromptManager."""


class PromptUnavailable(PromptManagerError):
    """Raised when both Supabase and the file fallback are unreachable.

    This is the refuse-to-boot signal — it means PromptManager cannot
    deliver a prompt and the caller (typically the runtime startup) should
    crash loudly rather than serve from stale or missing state.
    """


# ─── Supabase Protocol ──────────────────────────────────────────────────────


class _SupabaseLike(Protocol):
    """Subset of ReadClient that PromptManager needs.

    Defined as a Protocol so tests can pass any object with matching
    signatures — no need to construct a full ReadClient with httpx.
    """

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def patch(
        self, table: str, filters: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]: ...


# ─── PromptManager ─────────────────────────────────────────────────────────


class PromptManager:
    """Manages Helm agent prompts — Supabase canonical, file fallback.

    Initialize once at startup with a ReadClient and an optional
    file-fallback directory. `load(agent_role)` returns the active prompt
    string. `push` and `pull` are operator-facing CLI verbs (T0.B6 wires
    the `python -m memory.prompt` entrypoint).
    """

    TABLE = "helm_prompts"

    def __init__(
        self,
        supabase: _SupabaseLike,
        fallback_dir: Path | None = None,
    ) -> None:
        """fallback_dir contains files named `<agent_role>.md` (or whatever
        path you pass to the load/pull methods). When None, no file
        fallback is attempted — Supabase failure raises immediately."""
        self._supabase = supabase
        self._fallback_dir = fallback_dir

    # ── Load ────────────────────────────────────────────────────────────────

    async def load(self, agent_role: str, fallback_path: Path | None = None) -> str:
        """Return the active prompt for `agent_role`.

        Order of attempts:
          1. Supabase — read the active row for this role.
          2. File fallback — read `fallback_path` if provided, else
             `fallback_dir / <agent_role>.md`.
          3. Raise PromptUnavailable.

        The file path can be supplied per-call to support agents whose
        on-disk filename doesn't match the role name (helm_prime → helm_prompt.md).
        """
        # Try Supabase
        try:
            rows = await self._supabase.select(
                self.TABLE,
                {
                    "agent_role": f"eq.{agent_role}",
                    "active": "eq.true",
                    "select": "content,version",
                    "limit": "1",
                },
            )
            if rows:
                content = str(rows[0]["content"])
                version = rows[0].get("version")
                logger.info(
                    "prompt.loaded.supabase",
                    agent_role=agent_role,
                    version=version,
                    bytes=len(content),
                )
                return content
            logger.info("prompt.supabase.empty", agent_role=agent_role)
        except Exception as e:
            logger.warning(
                "prompt.supabase.unreachable",
                agent_role=agent_role,
                error=str(e)[:300],
                error_type=type(e).__name__,
            )

        # Fall back to file
        path = self._resolve_fallback_path(agent_role, fallback_path)
        if path is not None and path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                logger.warning(
                    "prompt.loaded.file_fallback",
                    agent_role=agent_role,
                    path=str(path),
                    bytes=len(content),
                )
                return content
            except OSError as e:
                logger.error(
                    "prompt.file_fallback.read_failed",
                    agent_role=agent_role,
                    path=str(path),
                    error=str(e),
                )

        # Both failed — refuse to serve
        raise PromptUnavailable(
            f"PromptManager.load({agent_role!r}): Supabase had no active prompt "
            f"and file fallback at {path} is missing or unreadable. Refusing to "
            "serve a stale or empty prompt."
        )

    # ── Push (file → Supabase) ─────────────────────────────────────────────

    async def push(
        self,
        agent_role: str,
        content: str,
        *,
        pushed_by: str = "cli",
        pushed_from: str = "file",
        notes: str | None = None,
    ) -> int:
        """Push `content` as a new active version for `agent_role`.

        Two writes happen in sequence:
          1. Deactivate any current active row for this role.
          2. Insert the new row with version = max(existing) + 1, active = true.

        Returns the new version number.

        If step 2 fails after step 1 succeeded, the role is left with no
        active prompt. Next push retries deactivation as a no-op + insert,
        restoring an active row. Loss tolerance: prompt history retains
        the deactivated rows for audit.
        """
        # Find current max version
        existing = await self._supabase.select(
            self.TABLE,
            {
                "agent_role": f"eq.{agent_role}",
                "select": "version",
                "order": "version.desc",
                "limit": "1",
            },
        )
        next_version = int(existing[0]["version"]) + 1 if existing else 1

        # Deactivate current active row (if any)
        await self._supabase.patch(
            self.TABLE,
            {"agent_role": agent_role, "active": "true"},
            {"active": False},
        )

        # Insert new active row
        payload: dict[str, Any] = {
            "agent_role": agent_role,
            "version": next_version,
            "content": content,
            "active": True,
            "pushed_by": pushed_by,
            "pushed_from": pushed_from,
        }
        if notes is not None:
            payload["notes"] = notes

        await self._supabase.insert(self.TABLE, payload)
        logger.info(
            "prompt.pushed",
            agent_role=agent_role,
            version=next_version,
            pushed_by=pushed_by,
            pushed_from=pushed_from,
            bytes=len(content),
        )
        return next_version

    # ── Pull (Supabase → file) ─────────────────────────────────────────────

    async def pull(self, agent_role: str, target_path: Path) -> int:
        """Pull the active prompt for `agent_role` and write it atomically
        to `target_path`. Returns the version pulled.

        Atomic via os.replace — same write-then-rename pattern that
        snapshot.py would have used. Cross-platform safe (Windows + POSIX).

        Raises PromptUnavailable if Supabase has no active row for the
        agent — pull does NOT fall back to reading the existing file
        (it's a Supabase → file operation; reverse is `load()`).
        """
        rows = await self._supabase.select(
            self.TABLE,
            {
                "agent_role": f"eq.{agent_role}",
                "active": "eq.true",
                "select": "content,version",
                "limit": "1",
            },
        )
        if not rows:
            raise PromptUnavailable(
                f"PromptManager.pull({agent_role!r}): no active prompt in Supabase."
            )
        content = str(rows[0]["content"])
        version = int(rows[0]["version"])

        # Atomic write: tempfile in the same dir, then os.replace.
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, target_path)

        logger.info(
            "prompt.pulled",
            agent_role=agent_role,
            version=version,
            target=str(target_path),
            bytes=len(content),
        )
        return version

    # ── List / history / activate (T0.B6 CLI surface) ──────────────────────

    async def list_active(self) -> list[dict[str, Any]]:
        """Return one row per agent_role: the currently active version.

        Cheap query for `python -m memory.prompt list`. Sorted by agent_role
        so output is deterministic.
        """
        rows: list[dict[str, Any]] = await self._supabase.select(
            self.TABLE,
            {
                "active": "eq.true",
                "select": "agent_role,version,pushed_by,pushed_from,notes,created_at",
                "order": "agent_role.asc",
            },
        )
        return rows

    async def list_versions(self, agent_role: str) -> list[dict[str, Any]]:
        """Return full version history for one agent_role, newest first.

        Backs `python -m memory.prompt history <role>`. Includes inactive
        rows so callers can see the audit trail of what was pushed when.
        """
        rows: list[dict[str, Any]] = await self._supabase.select(
            self.TABLE,
            {
                "agent_role": f"eq.{agent_role}",
                "select": "version,active,pushed_by,pushed_from,notes,created_at",
                "order": "version.desc",
            },
        )
        return rows

    async def activate(self, agent_role: str, version: int) -> None:
        """Flip a specific version to active.

        Deactivates the currently active row for this role first, then flips
        the target version's active flag to true. Raises PromptUnavailable
        if `version` doesn't exist for this role.

        Used by `python -m memory.prompt activate <role> <version>` for
        one-command revert to a known-good past prompt.
        """
        rows = await self._supabase.select(
            self.TABLE,
            {
                "agent_role": f"eq.{agent_role}",
                "version": f"eq.{version}",
                "select": "id,active",
                "limit": "1",
            },
        )
        if not rows:
            raise PromptUnavailable(
                f"PromptManager.activate({agent_role!r}, version={version}): "
                "no such version exists."
            )
        if bool(rows[0].get("active")):
            logger.info(
                "prompt.activate.noop",
                agent_role=agent_role,
                version=version,
                reason="already_active",
            )
            return

        await self._supabase.patch(
            self.TABLE,
            {"agent_role": agent_role, "active": "true"},
            {"active": False},
        )
        await self._supabase.patch(
            self.TABLE,
            {"agent_role": agent_role, "version": str(version)},
            {"active": True},
        )
        logger.info("prompt.activated", agent_role=agent_role, version=version)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _resolve_fallback_path(self, agent_role: str, explicit: Path | None) -> Path | None:
        """Per-call explicit path wins; otherwise look up
        fallback_dir/<agent_role>.md; else None."""
        if explicit is not None:
            return explicit
        if self._fallback_dir is not None:
            return self._fallback_dir / f"{agent_role}.md"
        return None
