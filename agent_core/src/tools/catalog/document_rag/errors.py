from __future__ import annotations


class DocumentRAGError(Exception):
    """Base exception for Document RAG pipeline failures."""


class DocumentDownloadError(DocumentRAGError):
    """Raised when a document cannot be downloaded from any supported source."""


class DocumentParseError(DocumentRAGError):
    """Raised when a downloaded document cannot be parsed into text blocks."""


class ChunkingError(DocumentRAGError):
    """Raised when semantic chunking fails or yields invalid chunks."""


class EmbeddingError(DocumentRAGError):
    """Raised when embedding generation fails."""


class ExtractionError(DocumentRAGError):
    """Raised when LLM extraction fails."""
