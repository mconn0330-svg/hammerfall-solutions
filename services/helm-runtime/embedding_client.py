"""
embedding_client.py — OpenAI embedding generation for Helm memory writes.

Wraps openai.AsyncOpenAI. Used by Archivist to generate embeddings before
writing to helm_memory. Embeddings enable match_memories() semantic search.

Model: text-embedding-3-small (1536 dimensions)
Only helm_memory is embedded at Stage 1. helm_beliefs and helm_entities
deferred to Stage 2.
"""

import logging
from typing import Optional

import openai

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._model = model
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def generate(self, text: str) -> Optional[list[float]]:
        """
        Generate an embedding vector for text.

        Returns a list[float] on success, None on failure.
        Failure is non-fatal — Archivist continues the write without embedding.
        A warning is logged so the gap is visible during BA5 testing.
        """
        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(
                "EmbeddingClient: generation failed — write will proceed without embedding. "
                "model=%s error=%s",
                self._model, e,
            )
            return None
