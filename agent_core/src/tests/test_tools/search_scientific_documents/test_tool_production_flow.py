import logging

import pytest

from tools.catalog.search_scientific_documents.tool import SearchScientificDocumentsTool


pytestmark = pytest.mark.integration_docker


def test_search_scientific_documents_production_flow(caplog, tool_test_logger):
    caplog.set_level(logging.INFO)
    tool = SearchScientificDocumentsTool()

    query = "silicon semiconductor band gap materials"
    tool_test_logger.info(
        "search_scientific_documents production_flow start query=%s",
        query,
    )
    result = tool.execute(
        query=query,
        providers=["arxiv"],
        max_results=3,
    )

    if result.status != "success":
        if result.error_code == "PROVIDER_FAILURE":
            pytest.skip(
                f"Provider unavailable in runtime environment: {result.error_detail}"
            )
        pytest.fail(
            f"Unexpected search tool error: {result.error_code} {result.error_detail}"
        )

    assert result.payload["count"] >= 1
    first = result.payload["documents"][0]
    assert first["source"] == "arxiv"
    assert first["title"]
    assert "relevance_score" in first
    assert "search_documents execute" in caplog.text
    assert "search_documents ranked=" in caplog.text
