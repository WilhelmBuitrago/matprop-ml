from fastapi.testclient import TestClient

from api.app import app
from api.security import reset_rate_limiter


def test_requires_api_key_when_enabled(monkeypatch, fake_requests_post):
    monkeypatch.setenv("AGENT_AUTH_MODE", "api_key")
    monkeypatch.setenv("AGENT_API_KEY", "top-secret")
    monkeypatch.setenv("AGENT_RATE_LIMIT_ENABLED", "false")
    reset_rate_limiter()

    client = TestClient(app)
    response = client.post("/v4/completions", json={"query": "find silicon"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_accepts_custom_api_key_header(monkeypatch, fake_requests_post):
    monkeypatch.setenv("AGENT_AUTH_MODE", "api_key")
    monkeypatch.setenv("AGENT_API_KEY", "top-secret")
    monkeypatch.setenv("AGENT_API_KEY_HEADER", "X-Agent-Key")
    monkeypatch.setenv("AGENT_RATE_LIMIT_ENABLED", "false")
    reset_rate_limiter()

    client = TestClient(app)
    response = client.post(
        "/v4/completions",
        headers={"X-Agent-Key": "top-secret"},
        json={"query": "find silicon"},
    )

    assert response.status_code == 200


def test_accepts_valid_api_key(monkeypatch, fake_requests_post):
    monkeypatch.setenv("AGENT_AUTH_MODE", "api_key")
    monkeypatch.setenv("AGENT_API_KEY", "top-secret")
    monkeypatch.setenv("AGENT_RATE_LIMIT_ENABLED", "false")
    reset_rate_limiter()

    client = TestClient(app)
    response = client.post(
        "/v4/completions",
        headers={"X-API-Key": "top-secret"},
        json={"query": "find silicon"},
    )

    assert response.status_code == 200
    assert "choices" in response.json()


def test_returns_429_when_rate_limit_exceeded(monkeypatch, fake_requests_post):
    monkeypatch.setenv("AGENT_AUTH_MODE", "disabled")
    monkeypatch.setenv("AGENT_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AGENT_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("AGENT_RATE_LIMIT_WINDOW_SECONDS", "60")
    reset_rate_limiter()

    client = TestClient(app)
    first = client.post("/v4/completions", json={"query": "find silicon"})
    second = client.post("/v4/completions", json={"query": "find silicon"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded"
