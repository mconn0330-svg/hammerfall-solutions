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

from typing import Any
from uuid import UUID

from observability import get_logger, tracer

from .client import MemoryClient
from .models import MemoryEntry, MemoryType, slugify

logger = get_logger("helm.memory.writer")


class MemoryWriter:
    """Write helmet for `helm_memory`. Wraps a `MemoryClient` with
    type-aware helpers."""

    def __init__(self, client: MemoryClient) -> None:
        self._client = client

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
    ) -> MemoryEntry:
        """Write a memory entry to `helm_memory` and return the persisted form.

        `memory_type` accepts either the `MemoryType` enum or its string
        value, so callers don't have to import the enum just to pass a
        literal type name.

        Returns the entry as constructed locally — id and timestamps are
        client-generated, so callers can reference them before Supabase
        confirms the insert (useful for outbox bookkeeping in T0.B2).
        """
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        entry = MemoryEntry(
            project=project,
            agent=agent,
            memory_type=memory_type,
            content=content,
            confidence=confidence,
            full_content=full_content,
            sync_ready=sync_ready,
            embedding=embedding,
            subject_ref=subject_ref,
        )

        with tracer.start_as_current_span("memory.write") as span:
            span.set_attribute("memory.project", project)
            span.set_attribute("memory.agent", agent)
            span.set_attribute("memory.type", memory_type.value)
            span.set_attribute("memory.entry_id", str(entry.id))

            payload = entry.to_supabase_payload()
            await self._client.insert("helm_memory", payload)
            logger.info(
                "memory.write",
                project=project,
                agent=agent,
                memory_type=memory_type.value,
                entry_id=str(entry.id),
                sync_ready=sync_ready,
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
    ) -> MemoryEntry:
        """Write a Projectionist frame.

        `full_content` carries the structured frame JSON; `content` is the
        1-3 sentence summary that lives in the warm/hot retrieval layer.
        """
        return await self.write(
            project=project,
            agent=agent,
            memory_type=MemoryType.FRAME,
            content=content,
            full_content=full_content,
            confidence=confidence,
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
