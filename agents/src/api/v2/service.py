"""Service layer for v2 API endpoints."""

from __future__ import annotations

import os
from typing import List

from ...models import EMBEDDING_MODEL
from ...services import (
    ChatService,
    CifService,
    InfoService,
    LoadModelsService,
    OllamaClient,
)

_DEFAULT_KEEP_ALIVE = "0s"


def resolve_keep_alive() -> str:
    raw = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", _DEFAULT_KEEP_ALIVE).strip()
    return raw if raw else _DEFAULT_KEEP_ALIVE


class V2RuntimeServices:
    """Factory for standardized v2 services using a shared Ollama client."""

    def __init__(self, keep_alive: str | None = None) -> None:
        self.keep_alive = keep_alive or resolve_keep_alive()
        self.ollama_client = OllamaClient(keep_alive=self.keep_alive)
        self.loader = LoadModelsService(ollama_client=self.ollama_client)
        self.chat = ChatService(ollama_client=self.ollama_client)
        self.cif = CifService(ollama_client=self.ollama_client)
        self.info = InfoService()


class EmbeddingsService:
    """Stateless embeddings service for v2 endpoints."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        keep_alive: str = "0s",
        client: OllamaClient | None = None,
    ):
        self.model = model
        self.client = client or OllamaClient(keep_alive=keep_alive)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        embeddings = self.client.embed_batch(self.model, texts)
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(embeddings)}, expected {len(texts)}"
            )
        return embeddings
