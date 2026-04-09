from api.v4.entry_policy import EntryPolicyV4


class _RegistryStub:
    def __init__(self, catalog: list[dict]):
        self._catalog = catalog

    def as_schema_catalog(self) -> list[dict]:
        return list(self._catalog)


def _catalog() -> list[dict]:
    return [
        {
            "name": "query_materials_database",
            "description": "Query materials by formula and band gap properties.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        },
        {
            "name": "search_scientific_documents",
            "description": "Search literature for material evidence.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        },
        {
            "name": "document_rag",
            "description": "Extract evidence from retrieved documents.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        },
    ]


def test_entry_policy_selection_is_deterministic_when_embeddings_fail(monkeypatch):
    policy = EntryPolicyV4(top_k=2)
    registry = _RegistryStub(_catalog())

    def _raise(*_args, **_kwargs):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(policy._embedding_cache, "initialize", _raise)

    first = policy.select_tools(
        query="compare candidate materials by band gap",
        registry=registry,
    )
    second = policy.select_tools(
        query="compare candidate materials by band gap",
        registry=registry,
    )

    assert [item["name"] for item in first] == [item["name"] for item in second]


def test_entry_policy_respects_top_k_bound():
    policy = EntryPolicyV4(top_k=10)
    registry = _RegistryStub(_catalog()[:2])

    selected = policy.select_tools(query="find materials", registry=registry)

    assert len(selected) == 2
