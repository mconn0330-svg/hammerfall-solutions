"""Tests for memory.models — MemoryType enum, MemoryEntry validation, slugify."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from memory.models import MemoryEntry, MemoryType, slugify

# ─── MemoryType enum ────────────────────────────────────────────────────────


def test_memory_type_has_all_tier_1_values() -> None:
    """Tier 1 catalog locked. New types append in T0.B7 — these never move."""
    expected = {
        "frame",
        "behavioral",
        "decision",
        "correction",
        "pattern",
        "observation",
        "monologue",
        "belief_update",
        "entity",
        "relationship",
        "scratchpad",
    }
    assert {t.value for t in MemoryType} == expected


def test_memory_type_round_trips_through_string() -> None:
    """Persisted as string in helm_memory.memory_type — must round-trip."""
    for t in MemoryType:
        assert MemoryType(t.value) is t


def test_memory_type_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        MemoryType("not_a_real_type")


# ─── slugify ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Small PRs strict merge order", "small-prs-strict-merge-order"),
        ("ALREADY-LOWERCASE-SLUG", "already-lowercase-slug"),
        ("  whitespace  edges  ", "whitespace-edges"),
        ("multi   spaces", "multi-spaces"),
        ("punct!@#$%^&*()-stripped", "punct-stripped"),
        ("---leading-trailing-hyphens---", "leading-trailing-hyphens"),
        ("digits 1234 ok", "digits-1234-ok"),
        ("", ""),
        ("   ", ""),
        ("!!!", ""),
    ],
)
def test_slugify_normalizes_correctly(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


def test_slugify_is_idempotent() -> None:
    """Already-slugged inputs survive a second pass unchanged. Important
    because write_pattern slugifies defensively even if the caller passes a
    real slug."""
    s = "small-prs-strict-merge-order"
    assert slugify(s) == s
    assert slugify(slugify(s)) == s


def test_slugify_truncates_to_max_len() -> None:
    long = "a" * 200
    assert len(slugify(long, max_len=50)) == 50


# ─── MemoryEntry ─────────────────────────────────────────────────────────────


def test_memory_entry_minimum_fields() -> None:
    """The smallest valid entry — required fields only, defaults fill rest."""
    e = MemoryEntry(
        project="hammerfall-solutions",
        agent="helm",
        memory_type=MemoryType.SCRATCHPAD,
        content="HEARTBEAT — ok",
    )
    assert isinstance(e.id, UUID)
    assert e.confidence is None
    assert e.full_content is None
    assert e.embedding is None
    assert e.subject_ref is None
    assert e.sync_ready is False
    assert e.synced_to_core is False
    # Timestamps default to "now-ish" — both UTC-aware
    assert e.created_at.tzinfo is not None
    assert e.created_at.utcoffset() == UTC.utcoffset(e.created_at)


def test_memory_entry_rejects_empty_strings() -> None:
    """Pydantic min_length=1 — empty project/agent/content is invalid."""
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="",
            agent="helm",
            memory_type=MemoryType.SCRATCHPAD,
            content="x",
        )
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="p",
            agent="",
            memory_type=MemoryType.SCRATCHPAD,
            content="x",
        )
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="p",
            agent="helm",
            memory_type=MemoryType.SCRATCHPAD,
            content="",
        )


def test_memory_entry_rejects_out_of_range_confidence() -> None:
    """Schema constraint: confidence in [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="p",
            agent="helm",
            memory_type=MemoryType.OBSERVATION,
            content="x",
            confidence=1.5,
        )
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="p",
            agent="helm",
            memory_type=MemoryType.OBSERVATION,
            content="x",
            confidence=-0.1,
        )


def test_memory_entry_accepts_string_memory_type_via_enum_construction() -> None:
    """Pydantic enum coercion — string values work for the type field."""
    e = MemoryEntry(
        project="p",
        agent="helm",
        memory_type="behavioral",
        content="x",
    )
    assert e.memory_type is MemoryType.BEHAVIORAL


def test_memory_entry_rejects_extra_fields() -> None:
    """extra='forbid' — unknown fields are validation errors, not silent ignores."""
    with pytest.raises(ValidationError):
        MemoryEntry(
            project="p",
            agent="helm",
            memory_type=MemoryType.SCRATCHPAD,
            content="x",
            unknown_field="value",  # type: ignore[call-arg]
        )


def test_to_supabase_payload_required_fields_only() -> None:
    """Optional fields stay out of the payload when None — lets Supabase
    apply column defaults rather than persisting NULLs."""
    e = MemoryEntry(
        project="hammerfall-solutions",
        agent="helm",
        memory_type=MemoryType.BEHAVIORAL,
        content="Decision: do the thing",
    )
    payload = e.to_supabase_payload()
    assert set(payload.keys()) == {
        "id",
        "project",
        "agent",
        "memory_type",
        "content",
        "session_date",
        "sync_ready",
        "synced_to_core",
        "created_at",
    }
    # Memory type serializes to its string value
    assert payload["memory_type"] == "behavioral"
    # ID is stringified
    assert payload["id"] == str(e.id)
    # session_date is ISO YYYY-MM-DD
    assert len(payload["session_date"]) == 10
    assert payload["session_date"].count("-") == 2


def test_to_supabase_payload_includes_optional_when_set() -> None:
    """When confidence/full_content/embedding/subject_ref are provided, they
    appear in the payload."""
    subj = uuid4()
    e = MemoryEntry(
        project="p",
        agent="helm",
        memory_type=MemoryType.OBSERVATION,
        content="x",
        confidence=0.85,
        full_content={"key": "value"},
        embedding=[0.1] * 1536,
        subject_ref=subj,
    )
    payload = e.to_supabase_payload()
    assert payload["confidence"] == 0.85
    assert payload["full_content"] == {"key": "value"}
    assert len(payload["embedding"]) == 1536
    assert payload["subject_ref"] == str(subj)


def test_memory_entry_id_is_unique_per_instance() -> None:
    """Default factory generates a fresh UUID per construction."""
    a = MemoryEntry(
        project="p",
        agent="helm",
        memory_type=MemoryType.SCRATCHPAD,
        content="x",
    )
    b = MemoryEntry(
        project="p",
        agent="helm",
        memory_type=MemoryType.SCRATCHPAD,
        content="x",
    )
    assert a.id != b.id


def test_created_at_serializes_with_offset() -> None:
    """Timestamps must serialize with explicit UTC offset — no naive dates
    leaking into Supabase timestamptz."""
    explicit = datetime(2026, 4, 26, 14, 30, 0, tzinfo=UTC)
    e = MemoryEntry(
        project="p",
        agent="helm",
        memory_type=MemoryType.SCRATCHPAD,
        content="x",
        created_at=explicit,
    )
    payload = e.to_supabase_payload()
    assert payload["created_at"] == "2026-04-26T14:30:00+00:00"
