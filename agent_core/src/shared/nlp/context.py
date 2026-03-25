from __future__ import annotations

from dataclasses import dataclass

from .similarity.base import Similarity
from .vectorizers.base import Vectorizer


@dataclass(frozen=True)
class SearchContext:
    vectorizer: Vectorizer
    similarity: Similarity
