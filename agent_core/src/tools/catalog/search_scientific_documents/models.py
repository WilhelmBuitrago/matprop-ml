from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    authors: list[str]
    year: int | None
    source: str
    doi: str | None
    url: str | None
    abstract: str | None
    citation_count: int | None


@dataclass(frozen=True)
class RawDocument:
    provider: str
    data: dict[str, Any]


@dataclass(frozen=True)
class Corpus:
    documents: list[Document]


@dataclass(frozen=True)
class TextCorpus:
    texts: list[str]
