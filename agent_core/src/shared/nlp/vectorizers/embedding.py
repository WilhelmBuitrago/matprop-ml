from __future__ import annotations

from .base import Vectorizer


class EmbeddingVectorizer(Vectorizer):
    def __init__(self, model) -> None:
        self.model = model

    def fit(self, corpus: list[str]) -> None:
        return None

    def transform(self, texts: list[str]):
        return [self.model.encode(text) for text in texts]
