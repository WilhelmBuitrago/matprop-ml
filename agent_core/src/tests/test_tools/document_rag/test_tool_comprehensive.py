import logging

import pytest

from api.v3.state import AgentState, BudgetState, DocumentRecord
from tools.catalog.document_rag.errors import (
    DocumentDownloadError,
    EmbeddingError,
    ExtractionError,
)
from tools.catalog.document_rag.models import ChunkScore, ParsedParagraph, SemanticChunk
from tools.catalog.document_rag.tool import DocumentRAGTool


pytestmark = pytest.mark.integration_docker


class _FakeDownloader:
    def __init__(self, responses: dict[str, object]):
        self._responses = responses

    def fetch_full_document(self, document: dict):
        action = self._responses.get(document.get("document_id"))
        if isinstance(action, Exception):
            raise action
        if action is None:
            raise DocumentDownloadError("missing_test_response")
        return action


class _FakeParser:
    def parse_document(self, payload: bytes, content_type: str):
        del payload, content_type
        return [
            ParsedParagraph(
                text=(
                    "Bismuth compounds show tunable band gaps under pressure and "
                    "strain when crystal symmetry is preserved."
                ),
                page=2,
                section="Results",
            ),
            ParsedParagraph(
                text=(
                    "Electronic transport remains anisotropic and strongly coupled to "
                    "defect chemistry in layered structures."
                ),
                page=2,
                section="Results",
            ),
        ]


class _FakeChunker:
    def chunk_document(self, document, paragraphs, max_chunks: int):
        del paragraphs
        if document.document_id.endswith("1"):
            first_text = "Bi2Se3 strain engineering changes band-gap windows and transport pathways."
            second_text = "Defect chemistry in Bi2Se3 controls carrier density and anisotropy signatures."
        else:
            first_text = "Bi2Te3 thermal transport is tuned by antisite defects and phonon scattering."
            second_text = "Layered tellurides show conductivity drifts under pressure and compositional gradients."

        return [
            SemanticChunk(
                chunk_id=f"{document.document_id}-1",
                document_id=document.document_id,
                title=document.title,
                doi=document.doi,
                url=document.url,
                page=2,
                section="Results",
                paragraph="Band-gap shift under lattice distortion.",
                text=first_text,
                tokens_count=76,
                document_relevance_score=document.relevance_score,
            ),
            SemanticChunk(
                chunk_id=f"{document.document_id}-2",
                document_id=document.document_id,
                title=document.title,
                doi=document.doi,
                url=document.url,
                page=3,
                section="Discussion",
                paragraph="Defect chemistry controls carrier concentration.",
                text=second_text,
                tokens_count=68,
                document_relevance_score=max(0.0, document.relevance_score - 0.15),
            ),
        ][:max_chunks]


class _FakeExtractor:
    def extract_for_chunk(self, query: str, chunk: ChunkScore):
        del query
        if chunk.chunk.chunk_id.endswith("-2"):
            raise ExtractionError("forced_extraction_failure")
        return ["Band gap narrows with pressure", "Symmetry retained in phase window"]


class _FallbackRetriever:
    client_is_none: list[bool] = []

    def __init__(
        self, embeddings_client, embedding_weight: float, keyword_weight: float
    ):
        del embedding_weight, keyword_weight
        self._embeddings_client = embeddings_client
        self.__class__.client_is_none.append(embeddings_client is None)

    def score_chunks(
        self,
        query_normalized: str,
        query_keywords: list[str],
        chunks: list[SemanticChunk],
    ):
        del query_normalized, query_keywords
        if self._embeddings_client is not None:
            raise EmbeddingError("forced_embeddings_failure")

        scored: list[ChunkScore] = []
        for idx, chunk in enumerate(chunks):
            keyword_score = max(0.35, 0.9 - (idx * 0.1))
            scored.append(
                ChunkScore(
                    chunk=chunk,
                    embedding_score=0.0,
                    keyword_score=keyword_score,
                    hybrid_score=keyword_score,
                    final_score=0.0,
                )
            )
        return scored


def _state_with_documents() -> AgentState:
    state = AgentState(
        request_id="rag-test",
        query="find evidence",
        intent="document_search",
        budget=BudgetState(),
    )
    state.documents.append(
        DocumentRecord(
            title="Bi-based semiconductors",
            source="semantic_scholar",
            relevance_score=0.9,
            abstract="summary",
        )
    )
    return state


def test_preconditions_require_documents_in_state(
    docker_env_for_tools, tool_test_logger
):
    del docker_env_for_tools
    tool = DocumentRAGTool()

    empty_state = AgentState(
        request_id="rag-empty",
        query="q",
        intent="document_search",
        budget=BudgetState(),
    )
    ok, reason = tool.preconditions(empty_state)

    tool_test_logger.info("document_rag preconditions checked for empty state")
    assert ok is False
    assert reason == "requires_documents_in_state"

    populated_state = _state_with_documents()
    ok, reason = tool.preconditions(populated_state)

    assert ok is True
    assert reason == ""


def test_execute_returns_validation_errors_for_missing_inputs(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    tool = DocumentRAGTool()
    caplog.set_level(logging.INFO)

    tool_test_logger.info("document_rag validating missing query")
    result_missing_query = tool.execute(documents=[{"document_id": "d1"}], query=" ")

    tool_test_logger.info("document_rag validating missing documents")
    result_missing_documents = tool.execute(query="band gap", documents=[])

    assert result_missing_query.status == "error"
    assert result_missing_query.error_code == "VALIDATION_ERROR"
    assert result_missing_query.error_detail == "query is required"

    assert result_missing_documents.status == "error"
    assert result_missing_documents.error_code == "VALIDATION_ERROR"
    assert result_missing_documents.error_detail == "documents must be a non-empty list"

    assert "document_rag validating missing query" in caplog.text
    assert "document_rag validating missing documents" in caplog.text


def test_execute_runs_pipeline_with_embedding_fallback_and_extraction_guard(
    docker_env_for_tools,
    monkeypatch,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    _FallbackRetriever.client_is_none = []
    monkeypatch.setattr(
        "tools.catalog.document_rag.tool.HybridRetriever", _FallbackRetriever
    )

    tool = DocumentRAGTool()
    tool.downloader = _FakeDownloader(
        responses={
            "doc-1": (b"pdf-content", "application/pdf", "10.7777/resolved-doi"),
            "doc-2": (b"pdf-content", "application/pdf", None),
        }
    )
    tool.parser = _FakeParser()
    tool.chunker = _FakeChunker()
    tool.extractor = _FakeExtractor()

    documents = [
        {
            "document_id": "doc-1",
            "title": "Pressure tuned Bi material",
            "doi": None,
            "url": "https://example.org/doc-1",
            "source": "semantic_scholar",
            "relevance_score": 0.88,
        },
        {
            "document_id": "doc-2",
            "title": "Defect chemistry in Bi compounds",
            "doi": "10.9999/original",
            "url": "https://example.org/doc-2",
            "source": "arxiv",
            "relevance_score": 0.75,
        },
    ]

    tool_test_logger.info("document_rag executing full pipeline with fallback scenario")
    result = tool.execute(
        query="band gap and conductivity",
        documents=documents,
        top_k=3,
        max_documents=2,
        max_chunks_per_document=2,
    )

    assert result.status == "success"
    assert len(result.payload["results"]) == 3

    first = result.payload["results"][0]
    assert first["document_id"] == "doc-1"
    assert first["doi"] == "10.7777/resolved-doi"
    assert first["extracted_info"]

    any_with_extraction_guard = [
        item for item in result.payload["results"] if item["extracted_info"] == []
    ]
    assert any_with_extraction_guard

    assert _FallbackRetriever.client_is_none == [False, True]
    assert "document_rag executing full pipeline with fallback scenario" in caplog.text


def test_execute_returns_no_documents_processed_when_pipeline_fails(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.WARNING)

    tool = DocumentRAGTool()
    tool.downloader = _FakeDownloader(
        responses={
            "doc-fail": DocumentDownloadError("download_failed_for_test"),
        }
    )

    documents = [
        {
            "document_id": "doc-fail",
            "title": "Unavailable source",
            "doi": None,
            "url": "https://example.org/unavailable",
            "source": "crossref",
            "relevance_score": 0.3,
        }
    ]

    tool_test_logger.warning("document_rag expects pipeline skip warning")
    result = tool.execute(query="band gap", documents=documents)

    assert result.status == "error"
    assert result.error_code == "NO_DOCUMENTS_PROCESSED"
    assert "Skipping document doc-fail due to pipeline failure" in caplog.text


def test_to_document_metadata_rejects_invalid_records_and_clamps_scores(
    docker_env_for_tools,
    tool_test_logger,
):
    del docker_env_for_tools
    tool = DocumentRAGTool()

    invalid = tool._to_document_metadata({"document_id": "", "title": "", "source": ""})
    assert invalid is None

    metadata = tool._to_document_metadata(
        {
            "document_id": "doc-99",
            "title": "  Structured Data  ",
            "source": "semantic_scholar",
            "doi": " ",
            "url": "",
            "relevance_score": 4.2,
        }
    )

    tool_test_logger.info("document_rag metadata normalization validated")
    assert metadata is not None
    assert metadata.doi is None
    assert metadata.url is None
    assert metadata.relevance_score == 1.0
