from __future__ import annotations

from api.v4.entry_policy import EntryPolicyV4


class _RegistryStub:
    def __init__(self, catalog: list[dict]):
        self._catalog = catalog

    def as_schema_catalog(self) -> list[dict]:
        return list(self._catalog)


def _catalog() -> list[dict]:
    return [
        {
            "name": "document_rag",
            "description": "Extract evidence from already collected documents.",
            "input_schema": {
                "type": "object",
                "properties": {"documents": {"type": "array"}},
            },
            "output_schema": {
                "type": "object",
                "properties": {"results": {"type": "array"}},
            },
        },
        {
            "name": "generate_crystal_structure",
            "description": "Generate CIF crystal structures from constraints.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            "output_schema": {
                "type": "object",
                "properties": {"cif": {"type": "string"}},
            },
        },
        {
            "name": "query_materials_database",
            "description": "Find materials by formula, material id, band gap and density properties.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "formula": {"type": "string"},
                    "material_id": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {"materials": {"type": "array"}},
            },
        },
    ]


def test_semantic_fallback_prefers_relevant_tool_when_embeddings_fail(monkeypatch):
    policy = EntryPolicyV4(top_k=2)
    registry = _RegistryStub(_catalog())

    def _raise(*args, **kwargs):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(policy._embedding_cache, "initialize", _raise)

    selected = policy.select_tools(
        query="find materials with target band gap in the database",
        registry=registry,
    )

    assert selected
    assert selected[0]["name"] == "query_materials_database"


def test_semantic_fallback_uses_regex_boost_for_exact_tool_name(monkeypatch):
    policy = EntryPolicyV4(top_k=1)
    registry = _RegistryStub(_catalog())

    def _raise(*args, **kwargs):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(policy._embedding_cache, "initialize", _raise)

    selected = policy.select_tools(
        query="run document_rag over the collected paper snippets",
        registry=registry,
    )

    assert selected
    assert selected[0]["name"] == "document_rag"


def test_semantic_fallback_is_deterministic_for_empty_query(monkeypatch):
    policy = EntryPolicyV4(top_k=2)
    registry = _RegistryStub(_catalog())

    def _raise(*args, **kwargs):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(policy._embedding_cache, "initialize", _raise)

    selected = policy.select_tools(query="", registry=registry)

    assert [item["name"] for item in selected] == [
        "document_rag",
        "generate_crystal_structure",
    ]
