from tools.catalog.search_scientific_documents.models import RawDocument
from tools.catalog.search_scientific_documents.providers.base import DocumentProvider
from tools.catalog.search_scientific_documents.tool import SearchScientificDocumentsTool


class _OkProvider(DocumentProvider):
    def __init__(self, name: str, docs: list[dict]):
        self.name = name
        self._docs = docs

    def search(self, query: str, limit: int) -> list[RawDocument]:
        return [RawDocument(provider=self.name, data=doc) for doc in self._docs[:limit]]


class _FailProvider(DocumentProvider):
    def __init__(self, name: str):
        self.name = name

    def search(self, query: str, limit: int) -> list[RawDocument]:
        raise RuntimeError("provider down")


def test_tool_executes_full_pipeline_with_mocked_providers():
    providers = {
        "semantic_scholar": _OkProvider(
            "semantic_scholar",
            [
                {
                    "paperId": "s2-1",
                    "title": "Band-gap engineering in Bi compounds",
                    "abstract": "A survey of tunable semiconductors",
                    "year": 2024,
                    "authors": [{"name": "Alice"}],
                    "doi": "10.1234/abc",
                    "url": "https://example.org/s2-1",
                    "citationCount": 12,
                }
            ],
        ),
        "arxiv": _OkProvider(
            "arxiv",
            [
                {
                    "id": "http://arxiv.org/abs/2401.12345",
                    "title": "Band-gap engineering in Bi compounds",
                    "summary": "Preprint version",
                    "published": "2024-01-20T00:00:00Z",
                    "authors": ["Alice"],
                }
            ],
        ),
    }

    tool = SearchScientificDocumentsTool(providers=providers)
    result = tool.execute(query="band gap", providers=["semantic_scholar", "arxiv"])

    assert result.status == "success"
    assert result.payload["count"] == 1
    doc = result.payload["documents"][0]
    assert doc["source"] == "semantic_scholar"
    assert doc["doi"] == "10.1234/abc"


def test_tool_returns_error_when_all_providers_fail():
    providers = {
        "arxiv": _FailProvider("arxiv"),
        "semantic_scholar": _FailProvider("semantic_scholar"),
    }

    tool = SearchScientificDocumentsTool(providers=providers)
    result = tool.execute(query="band gap", providers=["arxiv", "semantic_scholar"])

    assert result.status == "error"
    assert result.error_code == "PROVIDER_FAILURE"
