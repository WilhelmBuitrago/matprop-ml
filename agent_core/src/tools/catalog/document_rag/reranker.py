from __future__ import annotations

from difflib import SequenceMatcher

from .models import ChunkScore


class ChunkReranker:
    def __init__(self, chunk_weight: float = 0.6, document_weight: float = 0.4) -> None:
        self.chunk_weight = chunk_weight
        self.document_weight = document_weight

    def deduplicate(self, scores: list[ChunkScore]) -> list[ChunkScore]:
        deduped: list[ChunkScore] = []
        seen_ids: set[str] = set()

        for item in sorted(scores, key=lambda entry: entry.hybrid_score, reverse=True):
            chunk = item.chunk
            if chunk.chunk_id in seen_ids:
                continue

            is_near_duplicate = False
            for existing in deduped:
                ratio = SequenceMatcher(None, existing.chunk.text, chunk.text).ratio()
                if ratio > 0.95:
                    is_near_duplicate = True
                    break

            if is_near_duplicate:
                continue

            seen_ids.add(chunk.chunk_id)
            deduped.append(item)

        return deduped

    def rerank(self, scores: list[ChunkScore]) -> list[ChunkScore]:
        reranked: list[ChunkScore] = []
        for item in scores:
            final_score = (
                self.chunk_weight * item.hybrid_score
                + self.document_weight * item.chunk.document_relevance_score
            )
            reranked.append(
                ChunkScore(
                    chunk=item.chunk,
                    embedding_score=item.embedding_score,
                    keyword_score=item.keyword_score,
                    hybrid_score=item.hybrid_score,
                    final_score=max(0.0, min(1.0, final_score)),
                )
            )

        reranked.sort(
            key=lambda entry: (
                entry.final_score,
                entry.chunk.document_relevance_score,
                entry.chunk.tokens_count,
            ),
            reverse=True,
        )
        return reranked
