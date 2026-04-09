from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from services.agents_client.embeddings_client import AgentsEmbeddingsClient
from tools.base import ToolContract, ToolResult

from .chunking import SemanticChunker
from .downloader import DocumentDownloader
from .errors import (
    ChunkingError,
    DocumentDownloadError,
    DocumentParseError,
    EmbeddingError,
    ExtractionError,
)
from .extractor import InsightExtractor
from .models import DocumentMetadata, SemanticChunk
from .normalizer import normalize_query
from .parser import DocumentParser
from .reranker import ChunkReranker
from .retriever import HybridRetriever
from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA

if TYPE_CHECKING:
    from api.v4.state import AgentState

logger = logging.getLogger(__name__)


class DocumentRAGTool(ToolContract):
    """Retrieve full document content and extract query-relevant technical insights."""

    name = "document_rag"
    description = (
        "Retrieve full document content, perform semantic chunking, and extract "
        "structured, query-relevant information using hybrid retrieval."
    )
    input_schema = INPUT_SCHEMA
    output_schema = OUTPUT_SCHEMA

    def __init__(self) -> None:
        self.downloader = DocumentDownloader(timeout_seconds=10, max_retries=2)
        self.parser = DocumentParser()
        self.chunker = SemanticChunker(
            min_words=150, max_words=400, overlap_sentences=1
        )
        self.reranker = ChunkReranker(chunk_weight=0.6, document_weight=0.4)
        self.extractor = InsightExtractor()

        self.embeddings_client: AgentsEmbeddingsClient | None = None
        try:
            agents_url = os.getenv(
                "AGENTS_SERVICE_URL",
                os.getenv("AGENTS_URL", "http://agents:8003"),
            )
            self.embeddings_client = AgentsEmbeddingsClient(base_url=agents_url)
        except Exception as exc:  # pragma: no cover
            logger.warning("Embeddings client unavailable: %s", exc)

    def preconditions(self, state: "AgentState"):
        if not state.documents:
            return False, "requires_documents_in_state"
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        documents = kwargs.get("documents") or []
        query = str(kwargs.get("query") or "").strip()
        logger.info(
            "document_rag execute start documents=%d query_len=%d",
            len(documents) if isinstance(documents, list) else -1,
            len(query),
        )

        if not query:
            logger.warning("document_rag validation_error empty_query")
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="query is required",
            )

        if not isinstance(documents, list) or not documents:
            logger.warning("document_rag validation_error empty_documents")
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="documents must be a non-empty list",
            )

        top_k = int(kwargs.get("top_k", 10))
        max_documents = int(kwargs.get("max_documents", 5))
        max_chunks_per_document = int(kwargs.get("max_chunks_per_document", 20))

        selected_documents = sorted(
            documents,
            key=lambda item: float(item.get("relevance_score", 0.0)),
            reverse=True,
        )[:max_documents]
        logger.info(
            "document_rag selected_documents=%d top_k=%d max_chunks_per_document=%d",
            len(selected_documents),
            top_k,
            max_chunks_per_document,
        )

        all_chunks: list[SemanticChunk] = []
        for raw_doc in selected_documents:
            metadata = self._to_document_metadata(raw_doc)
            if metadata is None:
                logger.warning("document_rag skip invalid_metadata raw=%s", raw_doc)
                continue

            try:
                payload, content_type, resolved_doi = (
                    self.downloader.fetch_full_document(raw_doc)
                )
                logger.info(
                    "document_rag downloaded doc=%s content_type=%s bytes=%d",
                    metadata.document_id,
                    content_type,
                    len(payload),
                )
                if resolved_doi and not metadata.doi:
                    metadata = DocumentMetadata(
                        document_id=metadata.document_id,
                        title=metadata.title,
                        doi=resolved_doi,
                        url=metadata.url,
                        source=metadata.source,
                        relevance_score=metadata.relevance_score,
                    )
                parsed = self.parser.parse_document(payload, content_type)
                logger.info(
                    "document_rag parsed doc=%s paragraphs=%d",
                    metadata.document_id,
                    len(parsed),
                )
                chunks = self.chunker.chunk_document(
                    document=metadata,
                    paragraphs=parsed,
                    max_chunks=max_chunks_per_document,
                )
                all_chunks.extend(chunks)
                logger.info(
                    "document_rag chunked doc=%s chunks=%d total_chunks=%d",
                    metadata.document_id,
                    len(chunks),
                    len(all_chunks),
                )
            except (DocumentDownloadError, DocumentParseError, ChunkingError) as exc:
                logger.warning(
                    "Skipping document %s due to pipeline failure: %s",
                    metadata.document_id,
                    exc,
                )
                continue

        if not all_chunks:
            logger.error("document_rag no_documents_processed")
            return ToolResult(
                status="error",
                payload={},
                error_code="NO_DOCUMENTS_PROCESSED",
                error_detail="No documents could be downloaded and parsed",
            )

        query_normalized, query_keywords = normalize_query(query)
        retriever = HybridRetriever(
            embeddings_client=self.embeddings_client,
            embedding_weight=0.7,
            keyword_weight=0.3,
        )

        try:
            scored = retriever.score_chunks(
                query_normalized, query_keywords, all_chunks
            )
        except EmbeddingError:
            logger.warning("document_rag embedding_failed fallback=keyword_only")
            retriever = HybridRetriever(
                embeddings_client=None,
                embedding_weight=0.7,
                keyword_weight=0.3,
            )
            scored = retriever.score_chunks(
                query_normalized, query_keywords, all_chunks
            )

        deduped = self.reranker.deduplicate(scored)
        reranked = self.reranker.rerank(deduped)
        top_chunks = reranked[:top_k]
        logger.info(
            "document_rag retrieval scored=%d deduped=%d selected=%d",
            len(scored),
            len(deduped),
            len(top_chunks),
        )

        results = []
        for item in top_chunks:
            try:
                extracted_info = self.extractor.extract_for_chunk(
                    query=query, chunk=item
                )
            except ExtractionError:
                logger.warning(
                    "document_rag extraction_failed chunk=%s",
                    item.chunk.chunk_id,
                )
                extracted_info = []

            results.append(
                {
                    "document_id": item.chunk.document_id,
                    "doi": item.chunk.doi,
                    "url": item.chunk.url,
                    "title": item.chunk.title,
                    "page": item.chunk.page,
                    "section": item.chunk.section,
                    "paragraph": item.chunk.paragraph,
                    "chunk": item.chunk.text,
                    "score": round(item.final_score, 6),
                    "extracted_info": extracted_info,
                }
            )

        logger.info("document_rag success results=%d", len(results))
        return ToolResult(status="success", payload={"results": results})

    def _to_document_metadata(self, raw: dict[str, Any]) -> DocumentMetadata | None:
        document_id = str(raw.get("document_id") or "").strip()
        title = str(raw.get("title") or "").strip()
        source = str(raw.get("source") or "").strip()

        if not document_id or not title or not source:
            return None

        doi_raw = raw.get("doi")
        doi = (
            str(doi_raw).strip()
            if doi_raw is not None and str(doi_raw).strip()
            else None
        )
        url_raw = raw.get("url")
        url = (
            str(url_raw).strip()
            if url_raw is not None and str(url_raw).strip()
            else None
        )

        try:
            relevance_score = float(raw.get("relevance_score", 0.0))
        except (TypeError, ValueError):
            relevance_score = 0.0

        relevance_score = max(0.0, min(1.0, relevance_score))

        return DocumentMetadata(
            document_id=document_id,
            title=title,
            doi=doi,
            url=url,
            source=source,
            relevance_score=relevance_score,
        )
