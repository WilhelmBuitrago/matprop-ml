from __future__ import annotations

import math
from collections import Counter

from shared.nlp.tokenizer import tokenize

from .base import Vectorizer

SparseVector = dict[str, float]


class TFIDFVectorizer(Vectorizer):
    """Simple deterministic TF-IDF vectorizer with sparse outputs."""

    def __init__(self) -> None:
        self._idf: dict[str, float] = {}
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        num_docs = len(corpus)
        if num_docs == 0:
            self._idf = {}
            self._fitted = True
            return

        doc_freq: Counter[str] = Counter()
        for text in corpus:
            tokens = set(tokenize(text))
            for token in tokens:
                doc_freq[token] += 1

        self._idf = {
            token: math.log((1 + num_docs) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }
        self._fitted = True

    def transform(self, texts: list[str]) -> list[SparseVector]:
        if not self._fitted:
            raise RuntimeError("TFIDFVectorizer.transform called before fit")

        vectors: list[SparseVector] = []
        for text in texts:
            tokens = tokenize(text)
            if not tokens:
                vectors.append({})
                continue

            tf = Counter(tokens)
            total = float(len(tokens))
            vector: SparseVector = {}
            for token, count in tf.items():
                idf = self._idf.get(token)
                if idf is None:
                    continue
                vector[token] = (count / total) * idf
            vectors.append(vector)
        return vectors
