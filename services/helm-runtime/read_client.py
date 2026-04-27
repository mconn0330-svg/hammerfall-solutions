"""
read_client.py — Read-side Supabase REST client for the Helm Runtime Service.

Renamed from `supabase_client.py` in T0.B6 to make the write/read split
explicit:

  - Brain WRITES to `helm_memory` go through the memory module
    (`memory.MemoryWriter`) — durable, retried, outbox-backed.
  - Brain READS (helm_beliefs, helm_personality, helm_memory queries,
    `match_memories()` / `match_beliefs()` / `match_entities()` RPCs) come
    here. No outbox needed; failure means the caller falls back to whatever
    default makes sense (empty list, warn-and-continue).
  - SIBLING-TABLE writes that aren't durable cognitive memory — PATCHing
    helm_beliefs.strength, helm_personality.score, helm_frames.layer —
    also stay here. They are config-style modifies; failure means the row
    stays in its prior state, which is the right "queued for retry"
    behavior implicitly.
  - Operator config writes for `helm_prompts` (push/pull) also use this
    client — push is an explicit operator action, outbox queueing on a
    config write would mask operator-visible failures.

Anything writing to `helm_memory` should go through `memory.MemoryWriter`,
not here. This is the durable-memory invariant established in T0.B3.
"""

from typing import Any

import httpx


class SupabaseError(Exception):
    """Raised when a Supabase REST call returns an error response."""

    pass


class ReadClient:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.service_key = service_key
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _check_response(self, response: httpx.Response) -> Any:
        """
        Raise SupabaseError if the response body contains a Supabase error object.
        curl exit code is always 0 on HTTP errors — same rule applies to httpx:
        raise_for_status() catches transport errors; this catches API-level errors.
        """
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "code" in data:
            raise SupabaseError(
                f"Supabase error {data.get('code')}: {data.get('message', 'unknown')}"
            )
        return data

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a new row. Returns the inserted row."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/{table}",
                json=payload,
                headers=self._headers,
                timeout=10.0,
            )
            result: dict[str, Any] = self._check_response(response)
            return result

    async def patch(
        self, table: str, filters: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """PATCH rows matching filters. Returns updated rows."""
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/{table}?{query}",
                json=payload,
                headers=self._headers,
                timeout=10.0,
            )
            result: list[dict[str, Any]] = self._check_response(response)
            return result

    async def delete(self, table: str, filters: dict[str, Any]) -> None:
        """DELETE rows matching filters."""
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.url}/rest/v1/{table}?{query}",
                headers={**self._headers, "Prefer": ""},
                timeout=10.0,
            )
            response.raise_for_status()

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """GET rows with query params. Returns list of rows."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/{table}?{query}",
                headers=self._headers,
                timeout=10.0,
            )
            result: list[dict[str, Any]] = self._check_response(response)
            return result

    async def rpc(self, function_name: str, params: dict[str, Any]) -> Any:
        """Call a Supabase RPC (stored function). Returns the function's response."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/{function_name}",
                json=params,
                headers=self._headers,
                timeout=15.0,
            )
            return self._check_response(response)

    async def match_memories(
        self,
        query_embedding: list[float],
        project: str = "hammerfall-solutions",
        agent: str = "helm",
        threshold: float = 0.7,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic similarity search via match_memories() Supabase RPC.

        Returns rows ordered by cosine similarity descending.
        Each row: id, content, memory_type, confidence, session_date,
                  created_at, similarity.
        Returns [] if no matches exceed the threshold.
        """
        result: list[dict[str, Any]] = await self.rpc(
            "match_memories",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
                "filter_project": project,
                "filter_agent": agent,
            },
        )
        return result

    async def match_beliefs(
        self,
        query_embedding: list[float],
        threshold: float = 0.7,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic similarity search via match_beliefs() Supabase RPC.

        Searches active beliefs only. Returns rows ordered by cosine similarity descending.
        Each row: id, domain, belief, strength, active, created_at, similarity.
        """
        result: list[dict[str, Any]] = await self.rpc(
            "match_beliefs",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
            },
        )
        return result

    async def match_entities(
        self,
        query_embedding: list[float],
        threshold: float = 0.7,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic similarity search via match_entities() Supabase RPC.

        Searches active entities only. Returns rows ordered by cosine similarity descending.
        Each row: id, entity_type, name, summary, attributes, first_mentioned_at, similarity.
        """
        result: list[dict[str, Any]] = await self.rpc(
            "match_entities",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
            },
        )
        return result

    async def health_check(self) -> bool:
        """
        Confirm Supabase REST API is reachable and helm_frames is queryable.
        Returns True on success, False on any failure.
        """
        try:
            await self.select("helm_frames", {"select": "id", "limit": "1"})
            return True
        except Exception:
            return False
