"""Memory module Pydantic models, the MemoryType enum, and the slug utility.

The enum is the type catalog Helm writes against. Adding a Tier 2 type per
T0.B7 should be: append a value here + add a thin wrapper in writer.py + add
a migration. Goal is ~50 lines per new type — that's the test of whether the
T0.B1 abstraction held up.

`MemoryEntry` is the validation gate — every write through this module
constructs one of these before it touches Supabase. The schema is the source
of truth for column shape; this model mirrors it on the Python side.

`slugify` is the stable-identifier utility used by belief writes (T2.4) and
any other type that needs a deterministic key derived from human content.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ._time import utc_now


class MemoryType(StrEnum):
    """Catalog of memory entry types Helm writes to `helm_memory`.

    Order matters for stability — new values must be APPENDED, never
    inserted between existing values or renamed. The string values are the
    canonical identifiers persisted in `helm_memory.memory_type`.

    Tier 1 types (T0.B1):
        FRAME, BEHAVIORAL, DECISION, CORRECTION, PATTERN, OBSERVATION,
        MONOLOGUE, BELIEF_UPDATE, ENTITY, RELATIONSHIP, SCRATCHPAD

    Tier 2 types arrive in T0.B7 (curiosities, promises, etc.) by appending.
    """

    FRAME = "frame"
    BEHAVIORAL = "behavioral"
    DECISION = "decision"
    CORRECTION = "correction"
    PATTERN = "pattern"
    OBSERVATION = "observation"
    MONOLOGUE = "monologue"
    BELIEF_UPDATE = "belief_update"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    SCRATCHPAD = "scratchpad"
    CURIOSITY = "curiosity"  # T0.B7b — event in helm_memory about a curiosity formation/transition


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"^-+|-+$")


def slugify(text: str, max_len: int = 80) -> str:
    """Turn human-readable text into a stable lowercase-hyphenated slug.

    Idempotent on already-slugged input. Empty / whitespace-only input
    returns an empty string — the caller decides whether that's an error
    (most do; slugs are identity).
    """
    lowered = text.strip().lower()
    hyphenated = _SLUG_NON_ALNUM.sub("-", lowered)
    trimmed = _SLUG_TRIM.sub("", hyphenated)
    return trimmed[:max_len]


class MemoryEntry(BaseModel):
    """Canonical write payload for `helm_memory`.

    Schema source of truth lives in `supabase/migrations/`; this model is the
    Python-side validation gate. Fields:

    - `id`: client-side UUID. Lets the writer reference an entry before
      Supabase confirms the insert (useful for outbox bookkeeping in T0.B2).
    - `confidence`: 0.0..1.0 with optional None for entries that aren't
      probabilistic.
    - `full_content`: the photographic-memory layer; never loaded at session
      start, retrieved only via Routine 6.
    - `embedding`: 1536-dim vector for semantic search via `match_memories()`.
    - `subject_ref`: foreign key into `helm_entities` when the memory is
      *about* a specific entity.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    project: str = Field(..., min_length=1)
    agent: str = Field(..., min_length=1)
    memory_type: MemoryType
    content: str = Field(..., min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    full_content: dict[str, Any] | None = None
    session_date: date = Field(default_factory=lambda: utc_now().date())
    sync_ready: bool = False
    synced_to_core: bool = False
    embedding: list[float] | None = None
    subject_ref: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)

    def to_supabase_payload(self) -> dict[str, Any]:
        """Serialize for Supabase REST insert.

        UUIDs become strings, datetimes become ISO-8601 with UTC offset, the
        date column gets a YYYY-MM-DD string. Optional fields are omitted
        from the payload when None so PostgREST applies the column default
        rather than persisting an explicit NULL.
        """
        payload: dict[str, Any] = {
            "id": str(self.id),
            "project": self.project,
            "agent": self.agent,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "session_date": self.session_date.isoformat(),
            "sync_ready": self.sync_ready,
            "synced_to_core": self.synced_to_core,
            "created_at": self.created_at.isoformat(),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.full_content is not None:
            payload["full_content"] = self.full_content
        if self.embedding is not None:
            payload["embedding"] = self.embedding
        if self.subject_ref is not None:
            payload["subject_ref"] = str(self.subject_ref)
        return payload
