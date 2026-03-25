from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from .models import Document


@dataclass(frozen=True)
class RankWeights:
    embeddings: float = 0.6
    tfidf: float = 0.2
    citations: float = 0.1
    recency: float = 0.1


def build_text(doc: Document) -> str:
    return f"{doc.title} {doc.abstract or ''}".strip()


def min_max_scale(values: list[float]) -> list[float]:
    if not values:
        return []
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        return [0.0 for _ in values]
    denominator = max_value - min_value
    return [(value - min_value) / denominator for value in values]


def compute_citation_scores(documents: list[Document]) -> list[float]:
    raw_scores = [math.log((doc.citation_count or 0) + 1) for doc in documents]
    return min_max_scale(raw_scores)


def compute_recency_scores(
    documents: list[Document], now_year: int | None = None
) -> list[float]:
    if now_year is None:
        now_year = datetime.now(UTC).year

    raw_scores: list[float] = []
    for doc in documents:
        if doc.year is None:
            raw_scores.append(0.0)
            continue
        distance = max(0, now_year - doc.year)
        raw_scores.append(1.0 / (distance + 1.0))
    return min_max_scale(raw_scores)


def combine_scores(
    tfidf_scores: list[float] | None = None,
    embeddings_scores: list[float] | None = None,
    citation_scores: list[float] | None = None,
    recency_scores: list[float] | None = None,
    weights: RankWeights | None = None,
) -> list[float]:
    """
    Combine TF-IDF, embeddings, citation, and recency scores.

    Args:
        tfidf_scores: TF-IDF text similarity scores (0-1)
        embeddings_scores: Embeddings similarity scores (0-1)
        citation_scores: Citation count scores (0-1)
        recency_scores: Publication recency scores (0-1)
        weights: score weights (defaults to RankWeights())

    Returns:
        Combined normalized scores (0-1 range)
    """
    weights = weights or RankWeights()

    # Determine the number of documents
    num_docs = max(
        len(s)
        for s in [tfidf_scores, embeddings_scores, citation_scores, recency_scores]
        if s is not None
    )

    combined: list[float] = []
    for i in range(num_docs):
        score = 0.0

        if embeddings_scores is not None and i < len(embeddings_scores):
            score += weights.embeddings * embeddings_scores[i]

        if tfidf_scores is not None and i < len(tfidf_scores):
            score += weights.tfidf * tfidf_scores[i]

        if citation_scores is not None and i < len(citation_scores):
            score += weights.citations * citation_scores[i]

        if recency_scores is not None and i < len(recency_scores):
            score += weights.recency * recency_scores[i]

        combined.append(score)

    return combined
