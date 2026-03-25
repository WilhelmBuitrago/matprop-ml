from tools.catalog.search_scientific_documents.models import Document
from tools.catalog.search_scientific_documents.ranking import (
    RankWeights,
    combine_scores,
    compute_citation_scores,
    compute_recency_scores,
)


def _docs():
    return [
        Document(
            document_id="d1",
            title="doc1",
            authors=[],
            year=2021,
            source="semantic_scholar",
            doi=None,
            url=None,
            abstract=None,
            citation_count=100,
        ),
        Document(
            document_id="d2",
            title="doc2",
            authors=[],
            year=2024,
            source="arxiv",
            doi=None,
            url=None,
            abstract=None,
            citation_count=0,
        ),
    ]


def test_ranking_components_are_deterministic():
    documents = _docs()
    tfidf_scores = [0.2, 0.9]
    citation_scores = compute_citation_scores(documents)
    recency_scores = compute_recency_scores(documents, now_year=2026)

    first = combine_scores(
        tfidf_scores=tfidf_scores,
        citation_scores=citation_scores,
        recency_scores=recency_scores,
        weights=RankWeights(),
    )
    second = combine_scores(
        tfidf_scores=tfidf_scores,
        citation_scores=citation_scores,
        recency_scores=recency_scores,
        weights=RankWeights(),
    )

    assert first == second
