from tools.catalog.search_scientific_documents.deduplicator import deduplicate
from tools.catalog.search_scientific_documents.models import Document


def _doc(source: str, doi: str | None, abstract: str | None, citations: int | None):
    return Document(
        document_id=f"{source}-id",
        title="Band-gap tuning in Bi compounds",
        authors=["A. Author"],
        year=2024,
        source=source,
        doi=doi,
        url=None,
        abstract=abstract,
        citation_count=citations,
    )


def test_deduplicate_prefers_semantic_scholar_for_same_doi():
    arxiv = _doc("arxiv", "10.1234/example", None, None)
    semantic = _doc("semantic_scholar", "10.1234/example", "rich abstract", 20)

    deduped = deduplicate([arxiv, semantic])

    assert len(deduped) == 1
    winner = deduped[0]
    assert winner.source == "semantic_scholar"
    assert winner.abstract == "rich abstract"
    assert winner.citation_count == 20
