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

import re
from datetime import date
from typing import Any, Protocol
from uuid import UUID

from observability import get_logger, tracer

from ._time import utc_now
from .circuit_breaker import CircuitBreakerOpen
from .client import MemoryClient, MemoryWriteFailed
from .models import MemoryEntry, MemoryType, slugify
from .outbox import Outbox

logger = get_logger("helm.memory.writer")

# T0.B6 em-dash normalization (per V2 spec):
# Pattern detection downstream (T2.6 dual-write hook, graduation counting)
# matches on `content.startswith("Pattern — ")` using U+2014 EM DASH.
# Callers might type `Pattern --`, `Pattern -`, `Pattern—` (no space), or
# even `Pattern -- ` with double-hyphen — all should normalize to the
# canonical `Pattern — ` so detection never misses a real pattern entry
# because of typing variation.
_PATTERN_PREFIX_NORMALIZE = re.compile(r"^Pattern\s*(?:—|--|-|–)\s*")


def _normalize_pattern_content(content: str) -> str:
    """Normalize `Pattern -- foo` / `Pattern - foo` / `Pattern—foo` etc. to
    the canonical `Pattern — foo` (with U+2014 EM DASH + spaces).

    Idempotent on already-canonical input. No-op on non-pattern content.
    """
    if not _PATTERN_PREFIX_NORMALIZE.match(content):
        return content
    return _PATTERN_PREFIX_NORMALIZE.sub("Pattern — ", content, count=1)


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

        # T0.B6 em-dash normalization — Pattern entries written via the
        # generic write() path (rather than write_pattern) get the same
        # canonical prefix so dual-write detection downstream doesn't miss
        # them when the caller types `Pattern --` or `Pattern -`.
        content = _normalize_pattern_content(content)

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
        content = f"Pattern — {normalized_slug} | {statement} | domain: {domain}{scope_tag}"
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

    async def write_curiosity(
        self,
        *,
        project: str,
        agent: str,
        content: str,
        full_content: dict[str, Any] | None = None,
        subject_ref: UUID | None = None,
    ) -> MemoryEntry:
        """Write a curiosity event to helm_memory. T0.B7b.

        Distinct from `write_helm_curiosity_record()`: this records a memory
        event about a curiosity (formation, transition); the canonical
        curiosity row (with status, resolution, etc.) lives in helm_curiosities
        and is written via `write_helm_curiosity_record()`. Same pattern as
        write_entity (memory event) vs write_helm_entity_record (canonical row)."""
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.CURIOSITY,
            content=content,
            full_content=full_content,
            subject_ref=subject_ref,
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

    # ── helm_entities + helm_entity_relationships writers (T0.B7a) ─────────

    async def write_helm_entity_record(
        self,
        *,
        entity_type: str,
        name: str,
        aliases: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        summary: str | None = None,
        salience_decay: float | None = None,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """Write a row to `helm_entities` (NOT `helm_memory`).

        Distinct from `write_entity()`: this writes the canonical entity row
        (the thing); `write_entity()` writes a `helm_memory` event row about
        an entity (the mention). Most flows want both — write the record
        once when first encountered, then write events as the entity recurs.

        `entity_type` must satisfy the schema CHECK: one of person, project,
        concept, place, organization, tool, event, pet (T0.B7a extends the
        spec's 7-type list with 'pet' for entities like Sanchez/Krieger/Keeley
        that exist in production).

        Same durability contract as the other record writers: transport
        failure routes to the outbox when configured; otherwise propagates.
        """
        payload: dict[str, Any] = {
            "entity_type": entity_type,
            "name": name,
        }
        if aliases is not None:
            payload["aliases"] = aliases
        if attributes is not None:
            payload["attributes"] = attributes
        if summary is not None:
            payload["summary"] = summary
        if salience_decay is not None:
            payload["salience_decay"] = salience_decay
        if embedding is not None:
            payload["embedding"] = embedding

        with tracer.start_as_current_span("memory.write_helm_entity_record") as span:
            span.set_attribute("memory.entity_type", entity_type)
            span.set_attribute("memory.entity_name", name)
            try:
                await self._client.insert("helm_entities", payload)
                span.set_attribute("memory.delivery", "direct")
                logger.info(
                    "memory.write.helm_entities",
                    entity_type=entity_type,
                    name=name,
                    delivery="direct",
                )
                return payload
            except (MemoryWriteFailed, CircuitBreakerOpen) as e:
                if self._outbox is None:
                    span.set_attribute("memory.delivery", "failed")
                    raise
                row_id = await self._outbox.enqueue("helm_entities", payload)
                span.set_attribute("memory.delivery", "queued")
                span.set_attribute("memory.outbox_row_id", row_id)
                logger.warning(
                    "memory.write.helm_entities.queued",
                    entity_type=entity_type,
                    name=name,
                    outbox_row_id=row_id,
                    reason=type(e).__name__,
                    error=str(e)[:300],
                )
                return payload

    async def write_helm_entity_relationship_record(
        self,
        *,
        from_entity: UUID | str,
        to_entity: UUID | str,
        relationship: str,
        notes: str | None = None,
        confidence: float | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        """Write a row to `helm_entity_relationships`.

        Bidirectional convention is the caller's responsibility: callers
        write two rows per relationship, flipping the label by perspective
        (Maxwell→Kim 'spouse' / Kim→Maxwell 'spouse'; Maxwell→Emma 'parent'
        / Emma→Maxwell 'child'). The seed mechanism (`memory.seed`) treats
        each relationship entry as one direction; authors write two entries
        when both are needed.

        `confidence` (formerly `strength` pre-T0.B7a) is 0.0..1.0 — how sure
        Helm is the relationship exists. NULL is valid and means no score
        was assigned.

        `active` defaults to True. Set False to mark a retired relationship
        without deleting (audit trail preserved).
        """
        payload: dict[str, Any] = {
            "from_entity": str(from_entity),
            "to_entity": str(to_entity),
            "relationship": relationship,
            "active": active,
        }
        if notes is not None:
            payload["notes"] = notes
        if confidence is not None:
            payload["confidence"] = confidence

        with tracer.start_as_current_span("memory.write_helm_entity_relationship_record") as span:
            span.set_attribute("memory.from_entity", str(from_entity))
            span.set_attribute("memory.to_entity", str(to_entity))
            span.set_attribute("memory.relationship", relationship)
            try:
                await self._client.insert("helm_entity_relationships", payload)
                span.set_attribute("memory.delivery", "direct")
                logger.info(
                    "memory.write.helm_entity_relationships",
                    from_entity=str(from_entity),
                    to_entity=str(to_entity),
                    relationship=relationship,
                    delivery="direct",
                )
                return payload
            except (MemoryWriteFailed, CircuitBreakerOpen) as e:
                if self._outbox is None:
                    span.set_attribute("memory.delivery", "failed")
                    raise
                row_id = await self._outbox.enqueue("helm_entity_relationships", payload)
                span.set_attribute("memory.delivery", "queued")
                span.set_attribute("memory.outbox_row_id", row_id)
                logger.warning(
                    "memory.write.helm_entity_relationships.queued",
                    from_entity=str(from_entity),
                    to_entity=str(to_entity),
                    outbox_row_id=row_id,
                    reason=type(e).__name__,
                    error=str(e)[:300],
                )
                return payload

    # ── helm_curiosities writer (T0.B7b) ───────────────────────────────────

    async def write_helm_curiosity_record(
        self,
        *,
        project: str,
        question: str,
        agent: str = "helm",
        formed_from: UUID | str | None = None,
        priority: str | None = None,
        status: str = "open",
    ) -> dict[str, Any]:
        """Write a row to `helm_curiosities` (NOT `helm_memory`).

        Distinct from `write_curiosity()`: this writes the canonical curiosity
        row (the open question itself); `write_curiosity()` writes a memory
        event row to helm_memory about a curiosity formation/transition. Same
        pattern as write_helm_entity_record vs write_entity.

        `priority` must be 'low' | 'medium' | 'high' or NULL (not yet
        prioritized). `status` must satisfy the schema CHECK: open |
        investigating | resolved | abandoned. Both validated server-side
        by the migration's CHECK constraints.

        `formed_from` is the helm_memory.id that sparked this curiosity
        (audit trail). Optional — curiosities can be authored without a
        triggering memory entry (e.g., explicit Maxwell prompt).

        Same durability contract as the other record writers: transport
        failure routes to the outbox when configured; otherwise propagates.
        """
        payload: dict[str, Any] = {
            "project": project,
            "agent": agent,
            "question": question,
            "status": status,
        }
        if formed_from is not None:
            payload["formed_from"] = str(formed_from)
        if priority is not None:
            payload["priority"] = priority

        with tracer.start_as_current_span("memory.write_helm_curiosity_record") as span:
            span.set_attribute("memory.project", project)
            span.set_attribute("memory.curiosity_status", status)
            try:
                await self._client.insert("helm_curiosities", payload)
                span.set_attribute("memory.delivery", "direct")
                logger.info(
                    "memory.write.helm_curiosities",
                    project=project,
                    status=status,
                    delivery="direct",
                )
                return payload
            except (MemoryWriteFailed, CircuitBreakerOpen) as e:
                if self._outbox is None:
                    span.set_attribute("memory.delivery", "failed")
                    raise
                row_id = await self._outbox.enqueue("helm_curiosities", payload)
                span.set_attribute("memory.delivery", "queued")
                span.set_attribute("memory.outbox_row_id", row_id)
                logger.warning(
                    "memory.write.helm_curiosities.queued",
                    project=project,
                    status=status,
                    outbox_row_id=row_id,
                    reason=type(e).__name__,
                    error=str(e)[:300],
                )
                return payload


# ─── helm_curiosities lifecycle update (T0.B7b) ─────────────────────────────


class _PatchCapable(Protocol):
    """Subset of ReadClient the curiosity status updater needs.

    Status transitions are PATCH operations, not inserts — they don't go
    through MemoryClient (insert-only). They go through ReadClient.patch()
    same way Archivist's belief-strength PATCHes do.

    Defined as a Protocol so tests can pass any object with a matching
    signature.
    """

    async def patch(
        self, table: str, filters: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]: ...


_VALID_CURIOSITY_STATUSES = ("open", "investigating", "resolved", "abandoned")


async def update_curiosity_status(
    client: _PatchCapable,
    *,
    curiosity_id: UUID | str,
    new_status: str,
    resolution: str | None = None,
) -> None:
    """Transition a curiosity to a new lifecycle state.

    Lifecycle: open → investigating → resolved | abandoned.

    `resolution` is the text of how the curiosity was resolved (free-form).
    Set when transitioning to 'resolved'; ignored otherwise. When set,
    `resolved_at` is populated server-side via the same PATCH (sets the
    timestamp at write time so it matches when the resolution actually
    happened, not when a later read observes it).

    Validates `new_status` client-side against the same enum the schema
    CHECK constraint enforces — fail-fast with ValueError rather than
    surface a Postgres CHECK violation.

    Returns nothing — caller can re-read via read_curiosity if it needs
    the post-transition state.
    """
    if new_status not in _VALID_CURIOSITY_STATUSES:
        raise ValueError(
            f"new_status must be one of {_VALID_CURIOSITY_STATUSES}, got {new_status!r}"
        )

    payload: dict[str, Any] = {"status": new_status}
    if new_status == "resolved":
        payload["resolved_at"] = utc_now().isoformat()
        if resolution is not None:
            payload["resolution"] = resolution
    elif new_status == "abandoned":
        # Abandoned curiosities also get a resolved_at stamp (the moment
        # they were abandoned). Resolution text is optional but commonly
        # explains why.
        payload["resolved_at"] = utc_now().isoformat()
        if resolution is not None:
            payload["resolution"] = resolution

    await client.patch(
        "helm_curiosities",
        {"id": f"eq.{curiosity_id}"},
        payload,
    )

    logger.info(
        "memory.update.helm_curiosities.status",
        curiosity_id=str(curiosity_id),
        new_status=new_status,
        resolution_set=resolution is not None,
    )
