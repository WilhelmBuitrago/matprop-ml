from __future__ import annotations

import math
import os
from typing import Dict, List

from services.agents_client import AgentsEmbeddingsClient
from tools.base import ToolRegistry


class ToolEmbeddingCache:
    """In-memory cache for tool description embeddings used in planned policy mode."""

    def __init__(self, embeddings_client: AgentsEmbeddingsClient | None = None):
        base_url = os.getenv("AGENTS_SERVICE_URL", "http://agents:8000")
        self._embeddings_client = embeddings_client or AgentsEmbeddingsClient(
            base_url=base_url,
        )
        self._tool_embeddings: Dict[str, List[float]] = {}
        self._tool_descriptions: Dict[str, str] = {}
        self._initialized = False

    def initialize(self, registry: ToolRegistry) -> None:
        if self._initialized:
            return

        catalog = registry.as_schema_catalog()
        names: List[str] = []
        descriptions: List[str] = []
        for entry in catalog:
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            description = str(entry.get("description", "")).strip() or name
            names.append(name)
            descriptions.append(description)

        if not names:
            raise RuntimeError("Cannot initialize tool embeddings: empty tool catalog")

        vectors = self._embeddings_client.embed_texts(descriptions)
        if len(vectors) != len(names):
            raise RuntimeError(
                f"Tool embedding mismatch: got {len(vectors)}, expected {len(names)}"
            )

        self._tool_embeddings = {name: vector for name, vector in zip(names, vectors)}
        self._tool_descriptions = {
            name: description for name, description in zip(names, descriptions)
        }
        self._initialized = True

    def embed_query(self, query: str) -> List[float]:
        vectors = self._embeddings_client.embed_texts([query])
        if not vectors:
            raise RuntimeError("Query embedding response is empty")
        return vectors[0]

    def top_k(
        self,
        *,
        query_embedding: List[float],
        k: int = 3,
    ) -> List[dict[str, float | str]]:
        if not self._initialized:
            raise RuntimeError("ToolEmbeddingCache must be initialized before scoring")

        bounded_k = max(1, int(k))
        scored: List[dict[str, float | str]] = []
        for tool_name, tool_embedding in self._tool_embeddings.items():
            score = self._cosine_similarity(query_embedding, tool_embedding)
            scored.append(
                {
                    "name": tool_name,
                    "score": score,
                    "description": self._tool_descriptions.get(tool_name, ""),
                }
            )

        scored.sort(key=lambda item: (-float(item["score"]), str(item["name"])))
        return scored[:bounded_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2:
            return 0.0

        length = min(len(vec1), len(vec2))
        if length <= 0:
            return 0.0

        dot = sum(float(vec1[i]) * float(vec2[i]) for i in range(length))
        norm1 = math.sqrt(sum(float(vec1[i]) * float(vec1[i]) for i in range(length)))
        norm2 = math.sqrt(sum(float(vec2[i]) * float(vec2[i]) for i in range(length)))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)
