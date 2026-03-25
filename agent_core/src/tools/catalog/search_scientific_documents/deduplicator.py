from __future__ import annotations

import hashlib

from .models import Document

PROVIDER_PRIORITY = {
    "semantic_scholar": 3,
    "crossref": 2,
    "arxiv": 1,
}


def _title_hash(title: str) -> str:
    normalized = " ".join(title.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _dedup_key(doc: Document) -> str:
    return f"doi:{doc.doi.lower()}" if doc.doi else f"title:{_title_hash(doc.title)}"


def _prefer(primary: Document, challenger: Document) -> Document:
    primary_priority = PROVIDER_PRIORITY.get(primary.source, 0)
    challenger_priority = PROVIDER_PRIORITY.get(challenger.source, 0)

    winner = challenger if challenger_priority > primary_priority else primary
    loser = primary if winner is challenger else challenger

    return Document(
        document_id=winner.document_id,
        title=winner.title if winner.title else loser.title,
        authors=winner.authors if winner.authors else loser.authors,
        year=winner.year if winner.year is not None else loser.year,
        source=winner.source,
        doi=winner.doi or loser.doi,
        url=winner.url or loser.url,
        abstract=winner.abstract or loser.abstract,
        citation_count=(
            winner.citation_count
            if winner.citation_count is not None
            else loser.citation_count
        ),
    )


def deduplicate(documents: list[Document]) -> list[Document]:
    dedup_map: dict[str, Document] = {}
    ordered_unique_keys: list[str] = []

    for document in documents:
        doi_key = f"doi:{document.doi.lower()}" if document.doi else None
        title_key = f"title:{_title_hash(document.title)}"

        existing = None
        if doi_key and doi_key in dedup_map:
            existing = dedup_map[doi_key]
        elif title_key in dedup_map:
            existing = dedup_map[title_key]

        if existing is None:
            chosen = document
            if title_key not in dedup_map:
                ordered_unique_keys.append(title_key)
        else:
            chosen = _prefer(existing, document)

        dedup_map[title_key] = chosen
        if doi_key:
            dedup_map[doi_key] = chosen

    return [dedup_map[key] for key in ordered_unique_keys]
