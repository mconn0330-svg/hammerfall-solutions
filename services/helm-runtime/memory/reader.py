"""Memory module read-side helpers.

T0.B3 starts the read-path migration with a single helper — `read_frames()`
— for Archivist's cold-queue drain. Per V2 spec read-disposition table:

    | Frame read by Archivist  | Moves to memory.read_frames() | T0.B3 |
    | match_memories()         | Stays in read_client          | T0.B6 cosmetic |
    | match_beliefs()          | Stays in read_client          | Stage 2 |
    | helm_personality reads   | Stays in read_client          | Stage 2 |

T0.B6 renames `read_client.py` → `read_client.py` (the cosmetic part).
This module grows progressively as read paths migrate over time, but the
unified WRITE path (writer.py + outbox.py) is the load-bearing part.

Reads don't need outbox / circuit breaker semantics — failure means the
caller falls back to whatever default behavior makes sense (empty list,
warn-and-continue). The reader is a thin wrapper that documents the
intended call shape and centralizes the table/column names.
"""

from __future__ import annotations

from typing import Any, Protocol


class _SelectCapable(Protocol):
    """Subset of ReadClient the reader needs.

    Defined as a Protocol so tests can pass any object with a matching
    signature (no need to construct a full ReadClient).
    """

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...


async def read_frames(
    client: _SelectCapable,
    *,
    layer: str = "cold",
    select_cols: str = "*",
    order: str = "created_at.asc",
    session_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read frames from `helm_frames`.

    Args:
        client: anything with a `select(table, params)` method (Protocol).
        layer: warm | cold | hot. Defaults to cold (Archivist's drain target).
        select_cols: PostgREST select expression. Defaults to all columns.
        order: PostgREST order expression.
        session_id: optional filter — restrict to one session.
        limit: optional cap on rows returned.

    Returns:
        List of frame rows (dicts) ordered by `order`. Empty list if none.

    The shape is intentionally narrow — Archivist + future readers can call
    this with the same signature; the parameters cover every read pattern
    we have today (cold drain, session-scoped pre-load) without explosion.
    """
    params: dict[str, Any] = {
        "layer": f"eq.{layer}",
        "select": select_cols,
        "order": order,
    }
    if session_id is not None:
        params["session_id"] = f"eq.{session_id}"
    if limit is not None:
        params["limit"] = str(limit)
    return await client.select("helm_frames", params)


async def read_entities(
    client: _SelectCapable,
    *,
    entity_type: str | None = None,
    name: str | None = None,
    alias: str | None = None,
    active_only: bool = True,
    select_cols: str = "*",
    order: str = "last_mentioned_at.desc",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read entities from `helm_entities`.

    Args:
        client: anything with a `select(table, params)` method (Protocol).
        entity_type: filter to a single type (person/project/concept/place/
            organization/tool/event/pet). Validated server-side by the CHECK.
        name: exact-match name filter (case-sensitive at the PostgREST layer).
        alias: array-contains match (`aliases=cs.{<alias>}`). Used by the
            Routine 4 duplicate guard's "did we already see this nickname?"
            step.
        active_only: defaults True — exclude rows where `active=false`.
        select_cols: PostgREST select expression. Defaults to all columns.
        order: PostgREST order expression. Defaults to most-recently-mentioned
            first.
        limit: optional cap on rows returned.

    Returns:
        List of entity rows (dicts) ordered by `order`. Empty list if none.

    Filters compose with AND. Pass nothing to read all active entities,
    youngest-mention first.
    """
    params: dict[str, Any] = {
        "select": select_cols,
        "order": order,
    }
    if entity_type is not None:
        params["entity_type"] = f"eq.{entity_type}"
    if name is not None:
        params["name"] = f"eq.{name}"
    if alias is not None:
        # PostgREST array-contains: aliases=cs.{<alias>}
        # cs = "contains" (the array column contains the value).
        params["aliases"] = f"cs.{{{alias}}}"
    if active_only:
        params["active"] = "eq.true"
    if limit is not None:
        params["limit"] = str(limit)
    return await client.select("helm_entities", params)


async def read_open_curiosities(
    client: _SelectCapable,
    *,
    project: str,
    agent: str = "helm",
    select_cols: str = "*",
    order: str = "formed_at.desc",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read open curiosities (status = open) from `helm_curiosities`. T0.B7b.

    Used by the Prime context loader (top-N open curiosities to surface
    at session start) and by the future Curiosities widget (T1.7).

    Args:
        client: anything with a `select(table, params)` method (Protocol).
        project: project scope filter (required — curiosities are
            project-scoped per the schema).
        agent: defaults to 'helm' — the only agent that forms curiosities
            today, but the column exists for forward compat.
        select_cols: PostgREST select expression. Defaults to all columns.
        order: PostgREST order expression. Defaults to most-recently-formed
            first (the natural reading order for "what is Helm wondering").
        limit: optional cap on rows returned (e.g., top 5 for context loader).

    Returns:
        List of curiosity rows (dicts). Empty list if no opens exist.

    Filter is `status = 'open'` — investigating/resolved/abandoned are
    excluded. To read by id (any status), use `read_curiosity()`.
    """
    params: dict[str, Any] = {
        "select": select_cols,
        "order": order,
        "project": f"eq.{project}",
        "agent": f"eq.{agent}",
        "status": "eq.open",
    }
    if limit is not None:
        params["limit"] = str(limit)
    return await client.select("helm_curiosities", params)


async def read_curiosity(
    client: _SelectCapable,
    *,
    curiosity_id: str,
    select_cols: str = "*",
) -> dict[str, Any] | None:
    """Read a single curiosity by id. T0.B7b.

    Returns None if no row exists (rather than raising) — caller decides
    whether absence is an error in their context.
    """
    rows = await client.select(
        "helm_curiosities",
        {
            "id": f"eq.{curiosity_id}",
            "select": select_cols,
            "limit": "1",
        },
    )
    return rows[0] if rows else None
