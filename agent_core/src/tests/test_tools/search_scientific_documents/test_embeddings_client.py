from services.agents_client.embeddings_client import AgentsEmbeddingsClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_embeddings_client_uses_v2_endpoint_without_timeout(monkeypatch):
    captured = {}

    def _fake_post(url, json):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    monkeypatch.setattr(
        "services.agents_client.embeddings_client.requests.post", _fake_post
    )

    client = AgentsEmbeddingsClient(base_url="http://localhost:8000")
    embeddings = client.embed_texts(["doc-1", "doc-2"])

    assert captured["url"] == "http://localhost:8000/v2/embeddings"
    assert captured["json"] == {"texts": ["doc-1", "doc-2"]}
    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
