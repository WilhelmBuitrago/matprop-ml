from __future__ import annotations

import math

from .base import Similarity


class CosineSimilarity(Similarity):
    """Cosine similarity for sparse dictionary vectors."""

    def compute(self, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        if not vec1 or not vec2:
            return 0.0

        if len(vec1) > len(vec2):
            vec1, vec2 = vec2, vec1

        dot = sum(value * vec2.get(token, 0.0) for token, value in vec1.items())
        norm1 = math.sqrt(sum(value * value for value in vec1.values()))
        norm2 = math.sqrt(sum(value * value for value in vec2.values()))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)
