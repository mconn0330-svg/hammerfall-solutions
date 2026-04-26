"""Memory writer — the unified write interface.

`MemoryWriter.write()` is the canonical function; everything else is a thin
wrapper on top. Type-specific helpers (`write_frame`, `write_correction`,
etc.) exist for ergonomics — agent code reads cleaner with
`memory.write_frame(...)` than with positional arguments — but they all
funnel through the same path.

Adding a new type per T0.B7 is the test of whether the abstraction holds:

  1. Append `MemoryType.NEW_TYPE` in `models.py` (1 line)
  2. Add `write_new_type()` helper here (5–10 lines)
  3. Migration for any sibling table the new type needs
  4. Tests

That's the ~50-line target.

Stateless: no in-memory mutation here. Multiple writers sharing one client
is the intended pattern (one client = one HTTP pool = one circuit breaker).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from observability import get_logger, tracer

from .circuit_breaker import CircuitBreakerOpen
from .client import MemoryClient, MemoryWriteFailed
from .models import MemoryEntry, MemoryType, slugify
from .outbox import Outbox

logger = get_logger("helm.memory.writer")


class MemoryWriter:
    """Write helmet for `helm_memory`. Wraps a `MemoryClient` with
    type-aware helpers.

    Optional outbox: if provided, transport failures (`MemoryWriteFailed`,
    `CircuitBreakerOpen`) are caught and the entry is enqueued to the
    outbox for the drain loop to retry later. Caller sees a successful
    write — the data is durable either way.

    Without outbox, the original exception propagates so callers can decide
    how to handle. T0.B2 wires the outbox in production. Tests can omit it
    to assert the raw client-failure path.
    """

    def __init__(self, client: MemoryClient, outbox: Outbox | None = None) -> None:
        self._client = client
        self._outbox = outbox

    async def write(
        self,
        *,
        project: str,
        agent: str,
        memory_type: MemoryType | str,
        content: str,
        confidence: float | None = None,
        full_content: dict[str, Any] | None = None,
        sync_ready: bool = False,
        embedding: list[float] | None = None,
        subject_ref: UUID | None = None,
        session_date: date | None = None,
    ) -> MemoryEntry:
        """Write a memory entry to `helm_memory` and return the persisted form.

        `memory_type` accepts either the `MemoryType` enum or its string
        value, so callers don't have to import the enum just to pass a
        literal type name.

        Returns the entry as constructed locally — id and timestamps are
        client-generated, so callers can reference them before Supabase
        confirms the insert.

        Failure semantics:
          - Synchronous client succeeds → returns the entry, span tagged
            `memory.delivery=direct`.
          - Synchronous client fails (`MemoryWriteFailed`,
            `CircuitBreakerOpen`) AND outbox is configured → entry is
            enqueued to outbox, returns the entry, span tagged
            `memory.delivery=queued`. The drain loop will retry until
            success or dead-letter.
          - Synchronous client fails AND no outbox → the underlying
            exception propagates. Callers decide how to handle.
          - Validation failure (Pydantic) → `ValidationError` propagates.
            That's a caller bug, not a transport problem; outbox doesn't
            catch it.
        """
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        # session_date is optional — when None, MemoryEntry's default fires
        # (today in UTC). Frame migration (Archivist) passes the frame's
        # original session_date so the indexed column reflects when the
        # conversation actually happened, not when the drain ran.
        entry_kwargs: dict[str, Any] = {
            "project": project,
            "agent": agent,
            "memory_type": memory_type,
            "content": content,
            "confidence": confidence,
            "full_content": full_content,
            "sync_ready": sync_ready,
            "embedding": embedding,
            "subject_ref": subject_ref,
        }
        if session_date is not None:
            entry_kwargs["session_date"] = session_date
        entry = MemoryEntry(**entry_kwargs)

        with tracer.start_as_current_span("memory.write") as span:
            span.set_attribute("memory.project", project)
            span.set_attribute("memory.agent", agent)
            span.set_attribute("memory.type", memory_type.value)
            span.set_attribute("memory.entry_id", str(entry.id))

            payload = entry.to_supabase_payload()
            try:
                await self._client.insert("helm_memory", payload)
                span.set_attribute("memory.delivery", "direct")
                logger.info(
                    "memory.write",
                    project=project,
                    agent=agent,
                    memory_type=memory_type.value,
                    entry_id=str(entry.id),
                    sync_ready=sync_ready,
                    delivery="direct",
                )
                return entry
            except (MemoryWriteFailed, CircuitBreakerOpen) as e:
                if self._outbox is None:
                    # No durable backstop — caller wanted to see this.
                    span.set_attribute("memory.delivery", "failed")
                    raise
                # Enqueue + return — caller sees success, drain loop retries.
                row_id = await self._outbox.enqueue("helm_memory", payload)
                span.set_attribute("memory.delivery", "queued")
                span.set_attribute("memory.outbox_row_id", row_id)
                logger.warning(
                    "memory.write.queued",
                    project=project,
                    agent=agent,
                    memory_type=memory_type.value,
                    entry_id=str(entry.id),
                    outbox_row_id=row_id,
                    reason=type(e).__name__,
                    error=str(e)[:300],
                )
                return entry

    # ── Type-specific helpers — thin wrappers, all funnel through write() ──

    async def write_frame(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any],
        confidence: float | None = None,
        session_date: date | None = None,
    ) -> MemoryEntry:
        """Write a Projectionist frame.

        `full_content` carries the structured frame JSON; `content` is the
        1-3 sentence summary that lives in the warm/hot retrieval layer.

        `session_date` should be the date of the original conversation when
        Archivist migrates a cold frame from helm_frames (so the indexed
        column matches the frame's true date, not the drain run's date).
        Defaults to today via MemoryEntry's factory.
        """
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.FRAME,
            content=content,
            full_content=full_content,
            confidence=confidence,
            session_date=session_date,
        )

    async def write_behavioral(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
        sync_ready: bool = False,
    ) -> MemoryEntry:
        """Write a behavioral entry (significant decision, reasoning).

        Set `sync_ready=True` for SYNC-READY milestones the snapshot service
        should mirror to .md (T0.B4 territory).
        """
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.BEHAVIORAL,
            content=content,
            full_content=full_content,
            sync_ready=sync_ready,
        )

    async def write_correction(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Write a correction. Content should start with the `[CORRECTION]`
        tag per the agent prompt convention so Routine 0 surfaces it."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.CORRECTION,
            content=content,
            full_content=full_content,
        )

    async def write_pattern(
        self,
        *,
        project: str,
        agent: str,
        slug: str,
        statement: str,
        domain: str,
        scope: str = "user",
    ) -> MemoryEntry:
        """Write a pattern observation.

        `slug` MUST be stable across observations of the same pattern —
        graduation counting (Standing Rule, see helm_prompt.md) is an ILIKE
        prefix match. We slugify defensively in case the caller passes a
        loose string.

        `scope: system` flags the pattern as a universal Helm behavior;
        absent or `user` is the default per the prompt convention.
        """
        normalized_slug = slugify(slug)
        if not normalized_slug:
            raise ValueError(f"slug {slug!r} resolves to empty after normalization")
        scope_tag = f" | scope: {scope}" if scope != "user" else ""
        content = f"Pattern — {normalized_slug} | {statement} | " f"domain: {domain}{scope_tag}"
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.PATTERN,
            content=content,
        )

    async def write_observation(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        confidence: float | None = None,
    ) -> MemoryEntry:
        """Write an observation entry — Contemplator's flagged patterns."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.OBSERVATION,
            content=content,
            confidence=confidence,
        )

    async def write_monologue(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        embedding: list[float] | None = None,
    ) -> MemoryEntry:
        """Write a Contemplator monologue. Surfaced at next session start by
        Routine 0."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.MONOLOGUE,
            content=content,
            embedding=embedding,
        )

    async def write_belief_update(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Write a belief lifecycle event. T2.5 (belief history) consumes
        these to construct `helm_belief_history` rows."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.BELIEF_UPDATE,
            content=content,
            full_content=full_content,
        )

    async def write_entity(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
        subject_ref: UUID | None = None,
    ) -> MemoryEntry:
        """Write an entity event. The `helm_entities` row itself is a separate
        write (different table); this entry records the event in `helm_memory`
        with `subject_ref` pointing at the entity."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.ENTITY,
            content=content,
            full_content=full_content,
            subject_ref=subject_ref,
        )

    async def write_relationship(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Write a relationship event. Sibling write to `helm_entity_relationships`
        — this records the event narrative."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.RELATIONSHIP,
            content=content,
            full_content=full_content,
        )

    async def write_decision(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Write a decision entry — distinct from behavioral in that it
        captures a deliberated choice, not just a noticed pattern."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.DECISION,
            content=content,
            full_content=full_content,
        )

    async def write_scratchpad(
        self,
        *,
        project: str,
        agent: str,
        content: str,
    ) -> MemoryEntry:
        """Write a scratchpad / heartbeat entry. Transient session state —
        Routine 0 explicitly excludes scratchpad from session_start reads."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.SCRATCHPAD,
            content=content,
        )

    # ── helm_frames record writer (Projectionist, T0.B3) ───────────────────

    async def write_helm_frame_record(
        self,
        *,
        session_id: str,
        turn_number: int,
        layer: str,
        frame_status: str,
        frame_json: dict[str, Any],
    ) -> dict[str, Any]:
        """Write a row to `helm_frames` (NOT `helm_memory` — different table).

        Projectionist creates these as the conversation unfolds; Archivist
        later drains cold-layer rows into `helm_memory` with `memory_type=frame`
        via `write_frame()`. Two distinct operations on two distinct tables.

        Same durability contract as `write()`: client failure
        (`MemoryWriteFailed` / `CircuitBreakerOpen`) routes to the outbox
        when one is configured. Without outbox, the underlying exception
        propagates so callers can decide.

        Returns the payload as written. Frame rows have a Supabase-generated
        `id` UUID (not client-generated like `MemoryEntry`) — caller can
        re-query if it needs the persisted id, but most flows only care
        that the write was accepted.
        """
        payload: dict[str, Any] = {
            "session_id": session_id,
            "turn_number": turn_number,
            "layer": layer,
            "frame_status": frame_status,
            "frame_json": frame_json,
        }
        with tracer.start_as_current_span("memory.write_helm_frame_record") as span:
            span.set_attribute("memory.session_id", session_id)
            span.set_attribute("memory.turn_number", turn_number)
            span.set_attribute("memory.frame_layer", layer)
            span.set_attribute("memory.frame_status", frame_status)
            try:
                await self._client.insert("helm_frames", payload)
                span.set_attribute("memory.delivery", "direct")
                logger.info(
                    "memory.write.helm_frames",
                    session_id=session_id,
                    turn_number=turn_number,
                    layer=layer,
                    frame_status=frame_status,
                    delivery="direct",
                )
                return payload
            except (MemoryWriteFailed, CircuitBreakerOpen) as e:
                if self._outbox is None:
                    span.set_attribute("memory.delivery", "failed")
                    raise
                row_id = await self._outbox.enqueue("helm_frames", payload)
                span.set_attribute("memory.delivery", "queued")
                span.set_attribute("memory.outbox_row_id", row_id)
                logger.warning(
                    "memory.write.helm_frames.queued",
                    session_id=session_id,
                    turn_number=turn_number,
                    outbox_row_id=row_id,
                    reason=type(e).__name__,
                    error=str(e)[:300],
                )
                return payload
