import logging

import pytest

from tools.catalog.search_scientific_documents.models import RawDocument
from tools.catalog.search_scientific_documents.providers.base import DocumentProvider
from tools.catalog.search_scientific_documents.tool import SearchScientificDocumentsTool


pytestmark = pytest.mark.integration_docker


class _OkProvider(DocumentProvider):
    def __init__(self, name: str, docs: list[dict]):
        self.name = name
        self._docs = docs
        self.last_query = None
        self.last_limit = None

    def search(self, query: str, limit: int) -> list[RawDocument]:
        self.last_query = query
        self.last_limit = limit
        return [RawDocument(provider=self.name, data=doc) for doc in self._docs[:limit]]


class _FailProvider(DocumentProvider):
    def __init__(self, name: str):
        self.name = name

    def search(self, query: str, limit: int) -> list[RawDocument]:
        del query, limit
        raise RuntimeError(f"provider {self.name} down")


def test_execute_returns_validation_errors_for_bad_inputs(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    tool = SearchScientificDocumentsTool(providers={"arxiv": _OkProvider("arxiv", [])})

    tool_test_logger.info("search_documents validating missing query")
    missing_query = tool.execute(query="  ")

    tool_test_logger.info("search_documents validating invalid providers")
    invalid_providers = tool.execute(query="band gap", providers=["does-not-exist"])

    assert missing_query.status == "error"
    assert missing_query.error_code == "VALIDATION_ERROR"
    assert missing_query.error_detail == "query is required"

    assert invalid_providers.status == "error"
    assert invalid_providers.error_code == "VALIDATION_ERROR"
    assert invalid_providers.error_detail == "No valid providers selected"
    assert "search_documents validating missing query" in caplog.text


def test_execute_succeeds_when_at_least_one_provider_returns_data(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    arxiv = _OkProvider(
        "arxiv",
        [
            {
                "id": "http://arxiv.org/abs/2401.11111",
                "title": "Bismuth semiconductors under strain",
                "summary": "Experimental trends in band-gap tuning.",
                "published": "2024-01-05T00:00:00Z",
                "authors": ["Ana", "Luis"],
            }
        ],
    )
    failing = _FailProvider("semantic_scholar")

    tool = SearchScientificDocumentsTool(
        providers={"arxiv": arxiv, "semantic_scholar": failing},
        use_embeddings=False,
    )

    tool_test_logger.info(
        "search_documents executing partial provider failure scenario"
    )
    result = tool.execute(
        query="band gap",
        providers=["arxiv", "semantic_scholar"],
        max_results=5,
    )

    assert result.status == "success"
    assert result.payload["count"] == 1
    assert result.payload["documents"][0]["source"] == "arxiv"
    assert arxiv.last_query == "band gap"
    assert arxiv.last_limit == 5
    assert "search_documents executing partial provider failure scenario" in caplog.text


def test_execute_returns_provider_failure_when_all_providers_fail(docker_env_for_tools):
    del docker_env_for_tools

    tool = SearchScientificDocumentsTool(
        providers={
            "arxiv": _FailProvider("arxiv"),
            "semantic_scholar": _FailProvider("semantic_scholar"),
        },
        use_embeddings=False,
    )

    result = tool.execute(query="band gap", providers=["arxiv", "semantic_scholar"])

    assert result.status == "error"
    assert result.error_code == "PROVIDER_FAILURE"
    assert result.error_detail == "All providers failed"


def test_execute_deduplicates_and_keeps_high_priority_source(docker_env_for_tools):
    del docker_env_for_tools

    semantic = _OkProvider(
        "semantic_scholar",
        [
            {
                "paperId": "s2-duplicate-1",
                "title": "Band-gap engineering in Bi compounds",
                "abstract": "Curated abstract from indexed journal.",
                "year": 2024,
                "authors": [{"name": "Alice"}],
                "doi": "10.1234/abc",
                "url": "https://example.org/s2",
                "citationCount": 28,
            }
        ],
    )
    arxiv = _OkProvider(
        "arxiv",
        [
            {
                "id": "http://arxiv.org/abs/2402.22222",
                "title": "Band-gap engineering in Bi compounds",
                "summary": "Preprint text",
                "published": "2024-02-10T00:00:00Z",
                "authors": ["Alice"],
            }
        ],
    )

    tool = SearchScientificDocumentsTool(
        providers={"semantic_scholar": semantic, "arxiv": arxiv},
        use_embeddings=False,
    )

    result = tool.execute(
        query="band gap",
        providers=["semantic_scholar", "arxiv"],
        max_results=5,
    )

    assert result.status == "success"
    assert result.payload["count"] == 1
    doc = result.payload["documents"][0]
    assert doc["source"] == "semantic_scholar"
    assert doc["doi"] == "10.1234/abc"
    assert doc["abstract"] == "Curated abstract from indexed journal."


def test_execute_appends_material_focus_to_provider_query(docker_env_for_tools):
    del docker_env_for_tools

    arxiv = _OkProvider(
        "arxiv",
        [
            {
                "id": "http://arxiv.org/abs/2501.12345",
                "title": "Focus-aware retrieval",
                "summary": "Material-specific relevance test.",
                "published": "2025-01-10T00:00:00Z",
                "authors": ["Team"],
            }
        ],
    )

    tool = SearchScientificDocumentsTool(
        providers={"arxiv": arxiv}, use_embeddings=False
    )
    result = tool.execute(
        query="thermoelectric optimization",
        material_focus="Bi2Te3",
        providers=["arxiv"],
    )

    assert result.status == "success"
    assert "Bi2Te3" in arxiv.last_query
    assert arxiv.last_query.startswith("thermoelectric optimization")


def test_execute_returns_empty_success_when_all_documents_fail_normalization(
    docker_env_for_tools,
):
    del docker_env_for_tools

    broken = _OkProvider(
        "semantic_scholar",
        [
            {
                "paperId": "broken-1",
                "title": "",
                "abstract": "Missing title should be discarded",
                "year": 2024,
                "authors": [{"name": "Alice"}],
                "doi": "10.0000/broken",
                "url": "https://example.org/broken",
                "citationCount": 2,
            }
        ],
    )

    tool = SearchScientificDocumentsTool(
        providers={"semantic_scholar": broken},
        use_embeddings=False,
    )

    result = tool.execute(query="band gap", providers=["semantic_scholar"])

    assert result.status == "success"
    assert result.payload == {"documents": [], "count": 0}


def test_init_logs_warning_when_embeddings_client_unavailable(
    docker_env_for_tools,
    monkeypatch,
    caplog,
):
    del docker_env_for_tools
    caplog.set_level(logging.WARNING)

    class _BrokenEmbeddingsClient:
        def __init__(self, base_url: str):
            del base_url
            raise RuntimeError("embeddings bootstrap failed")

    monkeypatch.setattr(
        "tools.catalog.search_scientific_documents.tool.AgentsEmbeddingsClient",
        _BrokenEmbeddingsClient,
    )

    SearchScientificDocumentsTool(providers={"arxiv": _OkProvider("arxiv", [])})

    assert "Failed to initialize embeddings client" in caplog.text
