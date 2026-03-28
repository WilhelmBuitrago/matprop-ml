import logging

import pytest
import requests

from tools.catalog.document_rag.tool import DocumentRAGTool
from tools.catalog.search_scientific_documents.tool import SearchScientificDocumentsTool


pytestmark = pytest.mark.integration_docker


def _agents_up() -> bool:
    try:
        response = requests.get("http://agents:8003/v2/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def test_document_rag_production_flow(caplog, tool_test_logger):
    if not _agents_up():
        pytest.skip("agents service is not reachable from agent_core container")

    caplog.set_level(logging.INFO)

    search_tool = SearchScientificDocumentsTool(use_embeddings=False)
    search_result = search_tool.execute(
        query="silicon crystal structure arxiv",
        providers=["arxiv"],
        max_results=2,
    )
    if search_result.status != "success" or search_result.payload.get("count", 0) == 0:
        pytest.skip("No production documents available for document_rag flow")

    documents = search_result.payload["documents"][:1]

    tool = DocumentRAGTool()
    tool_test_logger.info(
        "document_rag production_flow start docs=%d query_len=%d",
        len(documents),
        len("extract key findings about structure and properties"),
    )
    result = tool.execute(
        documents=documents,
        query="extract key findings about structure and properties",
        top_k=1,
        max_documents=1,
        max_chunks_per_document=10,
    )

    if result.status == "error" and result.error_code == "NO_DOCUMENTS_PROCESSED":
        pytest.skip("Document download/parse unavailable in runtime environment")

    assert result.status == "success"
    assert "results" in result.payload
    assert len(result.payload["results"]) >= 1

    first = result.payload["results"][0]
    assert first["document_id"]
    assert first["title"]
    assert "score" in first
    assert "extracted_info" in first
    assert "document_rag execute start" in caplog.text
    assert "document_rag success" in caplog.text
