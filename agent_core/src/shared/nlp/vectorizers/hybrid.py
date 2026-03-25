"""Hybrid ranking combining dense embeddings and sparse TF-IDF."""

import logging
from typing import List

import numpy as np

from .base import Vectorizer
from .tfidf import TFIDFVectorizer
from ..similarity.cosine import CosineSimilarity

logger = logging.getLogger(__name__)


class HybridVectorizer(Vectorizer):
    """
    Orchestrate both embeddings and TF-IDF vectorization with fallback.

    Responsibilities:
    - Manage embeddings client (may be None)
    - Fit and transform for TF-IDF (always available)
    - Request embeddings with automatic fallback to TF-IDF only
    - Compute similarity scores for both components
    """

    def __init__(
        self,
        embeddings_client=None,
        use_embeddings: bool = True,
    ):
        """
        Initialize hybrid vectorizer.

        Args:
            embeddings_client: optional AgentsEmbeddingsClient (None = TF-IDF only)
            use_embeddings: whether to attempt embeddings request
        """
        self.embeddings_client = embeddings_client
        self.use_embeddings = use_embeddings and embeddings_client is not None
        self.tfidf_vectorizer = TFIDFVectorizer()
        self.cosine_similarity = CosineSimilarity()
        self._fitted = False
        self._embeddings_available = False

    def fit(self, corpus: List[str]) -> "HybridVectorizer":
        """
        Fit TF-IDF and test embeddings availability.

        Args:
            corpus: list of documents to fit

        Returns:
            self
        """
        if not corpus:
            raise ValueError("Corpus cannot be empty")

        # Always fit TF-IDF (required for fallback)
        self.tfidf_vectorizer.fit(corpus)

        # Test embeddings availability (non-fatal if unavailable)
        if self.use_embeddings:
            try:
                _ = self.embeddings_client.embed_texts(corpus[:1])
                self._embeddings_available = True
                logger.info("Embeddings service available and working")
            except Exception as exc:
                logger.warning(
                    "Embeddings service unavailable, using TF-IDF only: %s", exc
                )
                self._embeddings_available = False
        else:
            self._embeddings_available = False

        self._fitted = True
        return self

    def compute_tfidf_scores(
        self, query: str, document_texts: List[str]
    ) -> List[float]:
        """
        Compute TF-IDF similarity scores using cosine distance.

        Args:
            query: query text
            document_texts: list of document texts

        Returns:
            similarity scores (0-1 range)
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        query_vector = self.tfidf_vectorizer.transform([query])[0]
        doc_vectors = self.tfidf_vectorizer.transform(document_texts)

        scores = [
            self.cosine_similarity.compute(query_vector, doc_vec)
            for doc_vec in doc_vectors
        ]
        return scores

    def compute_embeddings_scores(
        self, query: str, document_texts: List[str]
    ) -> List[float] | None:
        """
        Compute embeddings similarity scores if available.

        Returns None if embeddings unavailable (fallback to TF-IDF only).

        Args:
            query: query text
            document_texts: list of document texts

        Returns:
            similarity scores (0-1 range) or None if unavailable
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        if not self._embeddings_available:
            return None

        try:
            # Get embeddings for query and documents
            all_texts = [query] + document_texts
            embeddings = self.embeddings_client.embed_texts(all_texts)

            if len(embeddings) != len(all_texts):
                logger.warning(
                    "Embedding count mismatch: got %d, expected %d",
                    len(embeddings),
                    len(all_texts),
                )
                return None

            query_embedding = embeddings[0]
            doc_embeddings = embeddings[1:]

            # Compute cosine similarity for dense vectors
            scores = []
            for doc_embedding in doc_embeddings:
                # Cosine similarity for dense vectors: dot product / (norm1 * norm2)
                dot_product = np.dot(query_embedding, doc_embedding)
                norm_query = np.linalg.norm(query_embedding)
                norm_doc = np.linalg.norm(doc_embedding)

                if norm_query > 0 and norm_doc > 0:
                    similarity = dot_product / (norm_query * norm_doc)
                    # Clamp to [0, 1] range
                    similarity = max(0.0, min(1.0, similarity))
                else:
                    similarity = 0.0

                scores.append(similarity)

            return scores
        except Exception as exc:
            logger.warning(
                "Embeddings computation failed, falling back to TF-IDF only: %s", exc
            )
            self._embeddings_available = False
            return None

    def transform(self, texts: List[str]):
        """
        Not implemented for hybrid vectorizer (use compute_* methods instead).

        Raises:
            NotImplementedError
        """
        raise NotImplementedError(
            "Use compute_tfidf_scores() and compute_embeddings_scores() instead"
        )
