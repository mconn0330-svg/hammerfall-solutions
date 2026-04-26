"""SQLite-backed durable outbox for memory writes.

The contract: once a write reaches the memory module, it is durable. If the
synchronous Supabase write succeeds, great. If it fails (network, 5xx,
circuit open), the entry is enqueued here and a background drain loop
retries until it lands or exhausts attempts and goes to the dead-letter
table for manual review.

Why SQLite (not JSONL):
  - ACID transactions on enqueue and drain (no concurrent-append races
    that bit v1's JSONL outbox)
  - Single-file portability (no Postgres dependency)
  - WAL mode = crash durability — process death mid-write doesn't corrupt
  - aiosqlite for async access — fits the runtime's asyncio model
  - Cross-platform (Linux containers, macOS, Windows)

Why a separate dead-letter table (not a column flag):
  - `outbox` queries become trivial — "everything pending"
  - Dead-letter triage is its own operational pattern (runbook 0009)
  - Replays can DELETE FROM outbox, then INSERT FROM dead_letter as a
    deliberate operation rather than an UPDATE that re-mixes states
"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import aiosqlite

from observability import get_logger, tracer

from ._time import utc_now

logger = get_logger("helm.memory.outbox")


# ─── Dataclasses ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OutboxStats:
    """Snapshot of outbox state. Surfaced via /health and Routine 0
    session_start_context."""

    queued_count: int
    dead_letter_count: int
    oldest_queued_at: str | None  # ISO-8601 UTC, or None if empty


@dataclass(frozen=True)
class DrainResult:
    """Result of one drain pass. Useful for tests + drain-loop logging."""

    drained: int
    failed: int
    dead_lettered: int


@dataclass
class OutboxEntry:
    """One pending row, as fetched for drain. Internal — not exported."""

    id: int
    table_name: str
    payload: dict[str, Any]
    queued_at: str
    attempt_count: int


# ─── Client protocol ────────────────────────────────────────────────────────


class _InsertCapable(Protocol):
    """Subset of MemoryClient that the outbox needs.

    Defined as a Protocol so tests can pass any object with a matching
    signature (no need to construct a full MemoryClient with a real httpx
    pool just to test drain behavior).
    """

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]: ...


# ─── Schema ─────────────────────────────────────────────────────────────────

# Both tables share the same shape. Dead-letter keeps the original queued_at
# (when the entry first entered the outbox) and gains a moved_at column so
# we can tell how long it sat before being given up on.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name      TEXT    NOT NULL,
    payload         TEXT    NOT NULL,
    queued_at       TEXT    NOT NULL,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    last_attempt_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_outbox_queued_at ON outbox(queued_at);

CREATE TABLE IF NOT EXISTS outbox_dead_letter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id     INTEGER NOT NULL,
    table_name      TEXT    NOT NULL,
    payload         TEXT    NOT NULL,
    queued_at       TEXT    NOT NULL,
    attempt_count   INTEGER NOT NULL,
    last_error      TEXT,
    moved_at        TEXT    NOT NULL
);
"""


class Outbox:
    """Durable async-safe write queue.

    Lifecycle:
        outbox = Outbox(settings.outbox_path)
        await outbox.connect()      # opens SQLite, applies schema
        ...
        await outbox.aclose()       # closes connection cleanly

    Background drain (typically started in service lifespan):
        drain_task = asyncio.create_task(outbox.drain_loop(client))
        ...
        drain_task.cancel()
        with suppress(asyncio.CancelledError):
            await drain_task
    """

    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_DRAIN_BATCH = 50
    DEFAULT_DRAIN_INTERVAL = 5.0

    def __init__(
        self,
        path: Path,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self._path = path
        self._max_attempts = max_attempts
        self._db: aiosqlite.Connection | None = None
        self._enqueue_lock = asyncio.Lock()  # serialize writes within a process

    @property
    def path(self) -> Path:
        return self._path

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    async def connect(self) -> None:
        """Open the SQLite file (creating parent dirs if needed) and apply
        the schema. Idempotent — safe to call multiple times."""
        if self._db is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self._path)
        # WAL: crash-durable, allows concurrent readers during writes
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.executescript(_SCHEMA)
        await db.commit()
        self._db = db
        logger.info("outbox.connected", path=str(self._path))

    async def aclose(self) -> None:
        """Close the SQLite connection. Safe to call multiple times."""
        if self._db is None:
            return
        await self._db.close()
        self._db = None
        logger.info("outbox.closed", path=str(self._path))

    def _require_connection(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Outbox.connect() must be called before use")
        return self._db

    # ── Enqueue ─────────────────────────────────────────────────────────────

    async def enqueue(self, table: str, payload: dict[str, Any]) -> int:
        """Append a write to the queue. Returns the row id.

        Async-safe: an internal lock serializes inserts within the process
        (SQLite supports concurrent enqueue across processes via WAL, but
        within one process aiosqlite needs serialization on the connection).
        """
        db = self._require_connection()
        queued_at = utc_now().isoformat()
        async with self._enqueue_lock:
            cursor = await db.execute(
                "INSERT INTO outbox (table_name, payload, queued_at) VALUES (?, ?, ?)",
                (table, json.dumps(payload), queued_at),
            )
            await db.commit()
            row_id = cursor.lastrowid
        if row_id is None:
            # aiosqlite always returns lastrowid for AUTOINCREMENT inserts.
            # Defensive: if SQLite ever changes, raise so the caller knows.
            raise RuntimeError("outbox enqueue returned no row id")
        logger.info("outbox.enqueued", table=table, row_id=row_id, queued_at=queued_at)
        return row_id

    # ── Drain ───────────────────────────────────────────────────────────────

    async def drain(
        self,
        client: _InsertCapable,
        batch_size: int = DEFAULT_DRAIN_BATCH,
    ) -> DrainResult:
        """Pull up to `batch_size` oldest entries and try to flush each.

        On success: DELETE the row.
        On failure: increment attempt_count, store last_error/last_attempt_at.
                    If attempt_count would exceed max_attempts, MOVE to
                    outbox_dead_letter (separate table for manual review).
        """
        db = self._require_connection()

        with tracer.start_as_current_span("memory.outbox.drain") as span:
            span.set_attribute("outbox.batch_size", batch_size)

            entries = await self._fetch_batch(db, batch_size)
            span.set_attribute("outbox.fetched", len(entries))
            if not entries:
                return DrainResult(drained=0, failed=0, dead_lettered=0)

            drained = 0
            failed = 0
            dead_lettered = 0

            for entry in entries:
                outcome = await self._attempt_one(db, client, entry)
                if outcome == "drained":
                    drained += 1
                elif outcome == "dead_lettered":
                    dead_lettered += 1
                else:
                    failed += 1

            span.set_attribute("outbox.drained", drained)
            span.set_attribute("outbox.failed", failed)
            span.set_attribute("outbox.dead_lettered", dead_lettered)
            logger.info(
                "outbox.drain_pass",
                drained=drained,
                failed=failed,
                dead_lettered=dead_lettered,
            )
            return DrainResult(drained=drained, failed=failed, dead_lettered=dead_lettered)

    async def _fetch_batch(self, db: aiosqlite.Connection, batch_size: int) -> list[OutboxEntry]:
        """Fetch the oldest pending entries. Ordered by id (which is
        AUTOINCREMENT and monotonic with insertion order)."""
        cursor = await db.execute(
            "SELECT id, table_name, payload, queued_at, attempt_count "
            "FROM outbox ORDER BY id ASC LIMIT ?",
            (batch_size,),
        )
        rows = await cursor.fetchall()
        return [
            OutboxEntry(
                id=int(row[0]),
                table_name=str(row[1]),
                payload=json.loads(row[2]),
                queued_at=str(row[3]),
                attempt_count=int(row[4]),
            )
            for row in rows
        ]

    async def _attempt_one(
        self,
        db: aiosqlite.Connection,
        client: _InsertCapable,
        entry: OutboxEntry,
    ) -> str:
        """Try to flush one entry. Returns "drained", "failed", or
        "dead_lettered"."""
        try:
            await client.insert(entry.table_name, entry.payload)
        except Exception as e:
            return await self._record_failure(db, entry, error=str(e))
        # Success — delete the row
        await db.execute("DELETE FROM outbox WHERE id = ?", (entry.id,))
        await db.commit()
        logger.info("outbox.drained_one", row_id=entry.id, table=entry.table_name)
        return "drained"

    async def _record_failure(
        self, db: aiosqlite.Connection, entry: OutboxEntry, error: str
    ) -> str:
        """Increment attempt_count or move to dead_letter if exhausted.
        Returns "failed" or "dead_lettered"."""
        next_attempt = entry.attempt_count + 1
        last_attempt_at = utc_now().isoformat()

        if next_attempt >= self._max_attempts:
            # Move to dead letter
            await db.execute(
                "INSERT INTO outbox_dead_letter "
                "(original_id, table_name, payload, queued_at, attempt_count, "
                " last_error, moved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.id,
                    entry.table_name,
                    json.dumps(entry.payload),
                    entry.queued_at,
                    next_attempt,
                    error,
                    last_attempt_at,
                ),
            )
            await db.execute("DELETE FROM outbox WHERE id = ?", (entry.id,))
            await db.commit()
            logger.critical(
                "outbox.dead_letter",
                original_id=entry.id,
                table=entry.table_name,
                attempts=next_attempt,
                error=error[:500],
            )
            return "dead_lettered"

        await db.execute(
            "UPDATE outbox SET attempt_count = ?, last_error = ?, last_attempt_at = ? "
            "WHERE id = ?",
            (next_attempt, error, last_attempt_at, entry.id),
        )
        await db.commit()
        logger.warning(
            "outbox.attempt_failed",
            row_id=entry.id,
            table=entry.table_name,
            attempt=next_attempt,
            max_attempts=self._max_attempts,
            error=error[:500],
        )
        return "failed"

    async def drain_loop(
        self,
        client: _InsertCapable,
        interval: float = DEFAULT_DRAIN_INTERVAL,
        batch_size: int = DEFAULT_DRAIN_BATCH,
    ) -> None:
        """Background worker: drain forever on `interval` cadence.

        Designed to run as an asyncio.Task started in the service lifespan.
        Cancellation is the clean shutdown signal — caller does
        `task.cancel(); await task` and the loop exits.

        Catches exceptions per-pass so one bad iteration doesn't kill the
        worker. Drain itself catches per-entry, so this layer mostly catches
        unexpected SQLite or asyncio errors.
        """
        logger.info("outbox.drain_loop.started", interval_seconds=interval)
        try:
            while True:
                try:
                    await self.drain(client, batch_size=batch_size)
                except Exception:
                    logger.exception("outbox.drain_loop.iteration_error")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("outbox.drain_loop.cancelled")
            raise

    # ── Stats / observability ──────────────────────────────────────────────

    async def stats(self) -> OutboxStats:
        """Snapshot of queue state. Cheap — three count/min queries."""
        db = self._require_connection()
        async with db.execute("SELECT COUNT(*) FROM outbox") as cursor:
            queued_row = await cursor.fetchone()
        async with db.execute("SELECT COUNT(*) FROM outbox_dead_letter") as cursor:
            dead_row = await cursor.fetchone()
        async with db.execute("SELECT MIN(queued_at) FROM outbox") as cursor:
            oldest_row = await cursor.fetchone()

        queued_count = int(queued_row[0]) if queued_row else 0
        dead_letter_count = int(dead_row[0]) if dead_row else 0
        oldest_queued_at = str(oldest_row[0]) if oldest_row and oldest_row[0] is not None else None

        return OutboxStats(
            queued_count=queued_count,
            dead_letter_count=dead_letter_count,
            oldest_queued_at=oldest_queued_at,
        )

    async def session_start_context(self) -> dict[str, Any]:
        """Surface outbox state for Helm's session_start awareness.

        Per V2 spec T0.B2: if writes are queued, Helm's next session-start
        brain read won't see his own recent writes — his memory will lie to
        him silently. This context lets Routine 0 (rewritten in T0.B6) hedge:
        "I think I told you about X earlier, but my memory is still settling."
        """
        s = await self.stats()
        return {
            "queued_count": s.queued_count,
            "dead_letter_count": s.dead_letter_count,
            "oldest_queued_at": s.oldest_queued_at,
        }


# ─── Helpers ────────────────────────────────────────────────────────────────


async def stop_drain_loop(task: asyncio.Task[None]) -> None:
    """Cancel a drain_loop task and await its clean exit. Convenience for
    service shutdown."""
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
