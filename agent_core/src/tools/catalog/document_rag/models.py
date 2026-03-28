from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentMetadata:
    document_id: str
    title: str
    doi: str | None
    url: str | None
    source: str
    relevance_score: float


@dataclass(frozen=True)
class ParsedParagraph:
    text: str
    page: int
    section: str


@dataclass(frozen=True)
class SemanticChunk:
    chunk_id: str
    document_id: str
    title: str
    doi: str | None
    url: str | None
    page: int
    section: str
    paragraph: str
    text: str
    tokens_count: int
    document_relevance_score: float


@dataclass(frozen=True)
class ChunkScore:
    chunk: SemanticChunk
    embedding_score: float
    keyword_score: float
    hybrid_score: float
    final_score: float
