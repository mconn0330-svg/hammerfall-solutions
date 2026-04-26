"""Memory module read-side helpers.

T0.B3 starts the read-path migration with a single helper — `read_frames()`
— for Archivist's cold-queue drain. Per V2 spec read-disposition table:

    | Frame read by Archivist  | Moves to memory.read_frames() | T0.B3 |
    | match_memories()         | Stays in read_client          | T0.B6 cosmetic |
    | match_beliefs()          | Stays in read_client          | Stage 2 |
    | helm_personality reads   | Stays in read_client          | Stage 2 |

T0.B6 renames `supabase_client.py` → `read_client.py` (the cosmetic part).
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
    """Subset of SupabaseClient the reader needs.

    Defined as a Protocol so tests can pass any object with a matching
    signature (no need to construct a full SupabaseClient).
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
