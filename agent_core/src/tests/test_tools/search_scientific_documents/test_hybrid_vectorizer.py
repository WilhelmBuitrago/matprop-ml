"""Tests for HybridVectorizer and embeddings integration."""

import pytest
from shared.nlp.vectorizers.hybrid import HybridVectorizer


class MockEmbeddingsClient:
    """Mock embeddings client for testing."""

    def __init__(self, available: bool = True):
        self.available = available
        self.embed_calls = []

    def embed_texts(self, texts):
        """Return mock embeddings or raise error if unavailable."""
        self.embed_calls.append(texts)
        if not self.available:
            raise RuntimeError("Embeddings service unavailable")
        # Return simple mock embeddings (normalized 1024-dim vectors)
        return [[float(i % 1024) / 1024.0 for i in range(1024)] for _ in texts]


def test_hybrid_vectorizer_with_embeddings():
    """Test HybridVectorizer with available embeddings service."""
    corpus = ["machine learning is great", "deep neural networks", "data science"]
    query = "machine learning"

    mock_client = MockEmbeddingsClient(available=True)
    vectorizer = HybridVectorizer(embeddings_client=mock_client, use_embeddings=True)

    # Fit should succeed with test
    vectorizer.fit(corpus)
    assert vectorizer._fitted
    assert vectorizer._embeddings_available

    # Compute TF-IDF scores
    tfidf_scores = vectorizer.compute_tfidf_scores(query, corpus)
    assert len(tfidf_scores) == len(corpus)
    assert all(0.0 <= s <= 1.0 for s in tfidf_scores)

    # Compute embeddings scores
    embeddings_scores = vectorizer.compute_embeddings_scores(query, corpus)
    assert embeddings_scores is not None
    assert len(embeddings_scores) == len(corpus)
    assert all(0.0 <= s <= 1.0 for s in embeddings_scores)


def test_hybrid_vectorizer_fallback_to_tfidf():
    """Test HybridVectorizer falls back to TF-IDF when embeddings unavailable."""
    corpus = ["machine learning is great", "deep neural networks", "data science"]
    query = "machine learning"

    mock_client = MockEmbeddingsClient(available=False)
    vectorizer = HybridVectorizer(embeddings_client=mock_client, use_embeddings=True)

    # Fit should detect unavailability
    vectorizer.fit(corpus)
    assert vectorizer._fitted
    assert not vectorizer._embeddings_available

    # TF-IDF scores still work
    tfidf_scores = vectorizer.compute_tfidf_scores(query, corpus)
    assert len(tfidf_scores) == len(corpus)

    # Embeddings return None (graceful fallback)
    embeddings_scores = vectorizer.compute_embeddings_scores(query, corpus)
    assert embeddings_scores is None


def test_hybrid_vectorizer_disabled_embeddings():
    """Test HybridVectorizer with embeddings explicitly disabled."""
    corpus = ["machine learning is great", "deep neural networks", "data science"]
    query = "machine learning"

    mock_client = MockEmbeddingsClient(available=True)
    vectorizer = HybridVectorizer(embeddings_client=mock_client, use_embeddings=False)

    # Fit with disabled embeddings
    vectorizer.fit(corpus)
    assert vectorizer._fitted
    assert not vectorizer._embeddings_available

    # TF-IDF still works
    tfidf_scores = vectorizer.compute_tfidf_scores(query, corpus)
    assert len(tfidf_scores) == len(corpus)

    # Embeddings return None when disabled
    embeddings_scores = vectorizer.compute_embeddings_scores(query, corpus)
    assert embeddings_scores is None


def test_hybrid_vectorizer_no_embeddings_client():
    """Test HybridVectorizer with no embeddings client (TF-IDF only)."""
    corpus = ["machine learning is great", "deep neural networks", "data science"]
    query = "machine learning"

    vectorizer = HybridVectorizer(embeddings_client=None)

    # Fit without embeddings client
    vectorizer.fit(corpus)
    assert vectorizer._fitted
    assert not vectorizer._embeddings_available

    # TF-IDF works
    tfidf_scores = vectorizer.compute_tfidf_scores(query, corpus)
    assert len(tfidf_scores) == len(corpus)

    # Embeddings return None without client
    embeddings_scores = vectorizer.compute_embeddings_scores(query, corpus)
    assert embeddings_scores is None


def test_hybrid_vectorizer_not_fitted_error():
    """Test HybridVectorizer raises error when not fitted."""
    vectorizer = HybridVectorizer()

    with pytest.raises(RuntimeError, match="not fitted"):
        vectorizer.compute_tfidf_scores("query", ["doc1"])


def test_hybrid_vectorizer_transform_not_implemented():
    """Test HybridVectorizer.transform() raises NotImplementedError."""
    corpus = ["machine learning is great", "deep neural networks", "data science"]
    vectorizer = HybridVectorizer()
    vectorizer.fit(corpus)

    with pytest.raises(NotImplementedError):
        vectorizer.transform(["query"])
