from __future__ import annotations

import math

from services.agents_client.embeddings_client import AgentsEmbeddingsClient

from .errors import EmbeddingError
from .models import ChunkScore, SemanticChunk
from .normalizer import tokenize_for_keywords


class HybridRetriever:
    def __init__(
        self,
        embeddings_client: AgentsEmbeddingsClient | None,
        embedding_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        self.embeddings_client = embeddings_client
        self.embedding_weight = embedding_weight
        self.keyword_weight = keyword_weight

    def score_chunks(
        self,
        query_normalized: str,
        query_keywords: list[str],
        chunks: list[SemanticChunk],
    ) -> list[ChunkScore]:
        if not chunks:
            return []

        embedding_scores = self._embedding_scores(query_normalized, chunks)
        scored: list[ChunkScore] = []

        for index, chunk in enumerate(chunks):
            keyword_score = self._keyword_score(query_keywords, chunk.text)
            embed_score = embedding_scores[index]
            if embed_score < 0:
                hybrid = keyword_score
                embed_score = 0.0
            else:
                hybrid = (
                    self.embedding_weight * embed_score
                    + self.keyword_weight * keyword_score
                )

            scored.append(
                ChunkScore(
                    chunk=chunk,
                    embedding_score=self._clamp(embed_score),
                    keyword_score=self._clamp(keyword_score),
                    hybrid_score=self._clamp(hybrid),
                    final_score=0.0,
                )
            )
        return scored

    def _embedding_scores(self, query: str, chunks: list[SemanticChunk]) -> list[float]:
        if self.embeddings_client is None:
            return [-1.0 for _ in chunks]

        texts = [query] + [chunk.text for chunk in chunks]
        try:
            vectors = self.embeddings_client.embed_texts(texts)
        except Exception as exc:
            raise EmbeddingError("embeddings_failed") from exc

        if len(vectors) != len(texts):
            raise EmbeddingError("embedding_count_mismatch")

        query_vector = vectors[0]
        return [self._cosine_to_unit(query_vector, vector) for vector in vectors[1:]]

    def _keyword_score(self, query_keywords: list[str], chunk_text: str) -> float:
        query_set = set(query_keywords)
        chunk_set = set(tokenize_for_keywords(chunk_text))
        if not query_set or not chunk_set:
            return 0.0
        intersection = len(query_set.intersection(chunk_set))
        union = len(query_set.union(chunk_set))
        if union == 0:
            return 0.0
        return intersection / union

    def _cosine_to_unit(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0

        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        cosine = dot / (left_norm * right_norm)
        return self._clamp((cosine + 1.0) / 2.0)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
