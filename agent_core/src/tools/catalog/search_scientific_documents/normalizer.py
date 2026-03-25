from __future__ import annotations

import hashlib
from typing import Any

from .errors import NormalizationError
from .models import Document, RawDocument


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_year(raw_year: Any) -> int | None:
    if raw_year is None:
        return None
    if isinstance(raw_year, int):
        return raw_year
    year_text = _clean(raw_year)
    if not year_text:
        return None
    if len(year_text) >= 4 and year_text[:4].isdigit():
        return int(year_text[:4])
    if year_text.isdigit() and len(year_text) == 4:
        return int(year_text)
    return None


def _normalize_authors(raw_authors: Any) -> list[str]:
    if raw_authors is None:
        return []
    authors: list[str] = []
    if isinstance(raw_authors, list):
        for entry in raw_authors:
            if isinstance(entry, dict):
                name = _clean(entry.get("name"))
            else:
                name = _clean(entry)
            if name:
                authors.append(name)
    return authors


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def normalize(raw: RawDocument) -> Document:
    """Normalize provider payload into strict internal Document."""
    provider = raw.provider
    data = raw.data

    title = ""
    abstract = None
    year = None
    authors: list[str] = []
    doi = None
    url = None
    citation_count = None
    source_id = ""

    if provider == "arxiv":
        source_id = _clean(data.get("id"))
        title = _clean(data.get("title"))
        abstract = _clean(data.get("summary")) or None
        year = _parse_year(data.get("published"))
        authors = _normalize_authors(data.get("authors"))
        url = source_id or None

    elif provider == "semantic_scholar":
        source_id = _clean(data.get("paperId"))
        title = _clean(data.get("title"))
        abstract = _clean(data.get("abstract")) or None
        year = _parse_year(data.get("year"))
        authors = _normalize_authors(data.get("authors"))
        doi = _clean(data.get("doi")) or None
        url = _clean(data.get("url")) or None
        raw_citations = data.get("citationCount")
        citation_count = int(raw_citations) if isinstance(raw_citations, int) else None

    elif provider == "crossref":
        source_id = _clean(data.get("DOI") or data.get("id"))
        title_list = data.get("title") or []
        title = _clean(
            title_list[0] if isinstance(title_list, list) and title_list else ""
        )
        abstract = _clean(data.get("abstract")) or None
        published_parts = (
            data.get("published-print", {}).get("date-parts")
            or data.get("published-online", {}).get("date-parts")
            or []
        )
        if published_parts and isinstance(published_parts, list) and published_parts[0]:
            year = _parse_year(published_parts[0][0])
        authors = _normalize_authors(data.get("author"))
        doi = _clean(data.get("DOI")) or None
        url = _clean(data.get("URL")) or None
        is_referenced_by_count = data.get("is-referenced-by-count")
        citation_count = (
            int(is_referenced_by_count)
            if isinstance(is_referenced_by_count, int)
            else None
        )

    else:
        raise NormalizationError(f"Unsupported provider: {provider}")

    title = " ".join(title.split())
    if not title:
        raise NormalizationError("Missing title")

    source_key = source_id or doi or title.lower()
    document_id = _stable_hash(f"{provider}:{source_key}")

    return Document(
        document_id=document_id,
        title=title,
        authors=authors,
        year=year,
        source=provider,
        doi=doi,
        url=url,
        abstract=abstract,
        citation_count=citation_count,
    )
