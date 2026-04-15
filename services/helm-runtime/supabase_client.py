"""
supabase_client.py — Thin Supabase REST client for the Helm Runtime Service.

Replaces brain.sh subprocess calls inside the Python service.
Both Projectionist and Archivist use this for all Supabase reads and writes.

Relationship to brain.sh:
  brain.sh remains the canonical write tool for Claude Code shell contexts
  (Helm Prime, Routine 4, snapshot.sh, sync_projects.sh). It is NOT replaced
  globally. This module is the Python equivalent used exclusively within the
  Helm Runtime Service. Two contexts, two tools, one Supabase endpoint.
"""

import httpx
from typing import Any


class SupabaseError(Exception):
    """Raised when a Supabase REST call returns an error response."""
    pass


class SupabaseClient:
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

    async def insert(self, table: str, payload: dict) -> dict:
        """POST a new row. Returns the inserted row."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/{table}",
                json=payload,
                headers=self._headers,
                timeout=10.0,
            )
            return self._check_response(response)

    async def patch(self, table: str, filters: dict, payload: dict) -> list:
        """PATCH rows matching filters. Returns updated rows."""
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/{table}?{query}",
                json=payload,
                headers=self._headers,
                timeout=10.0,
            )
            return self._check_response(response)

    async def delete(self, table: str, filters: dict) -> None:
        """DELETE rows matching filters."""
        query = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.url}/rest/v1/{table}?{query}",
                headers={**self._headers, "Prefer": ""},
                timeout=10.0,
            )
            response.raise_for_status()

    async def select(self, table: str, params: dict) -> list:
        """GET rows with query params. Returns list of rows."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/{table}?{query}",
                headers=self._headers,
                timeout=10.0,
            )
            return self._check_response(response)

    async def rpc(self, function_name: str, params: dict) -> Any:
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
        query_embedding: list,
        project: str = "hammerfall-solutions",
        agent: str = "helm",
        threshold: float = 0.7,
        count: int = 10,
    ) -> list:
        """
        Semantic similarity search via match_memories() Supabase RPC.

        Returns rows ordered by cosine similarity descending.
        Each row: id, content, memory_type, confidence, session_date,
                  created_at, similarity.
        Returns [] if no matches exceed the threshold.
        """
        return await self.rpc(
            "match_memories",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
                "filter_project": project,
                "filter_agent": agent,
            },
        )

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
