import os
import sys
from typing import Any, Dict
import logging

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


@pytest.fixture
def fake_requests_post(monkeypatch):
    """Stub requests.post used by evaluator and final response generation."""

    class _Resp:
        def __init__(self, payload: Dict[str, Any]):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _post(url, json=None, headers=None, timeout=None):
        if url.endswith("/v2/insights"):
            return _Resp({"insights": ["Fact A", "Fact B"]})

        if (
            url.endswith("/v2/completions")
            and json
            and "strict json" in str(json).lower()
        ):
            return _Resp(
                {
                    "response": '{"verdict": "insufficient", "confidence": 0.65, '
                    '"missing_information": ["comparison"], "risk_if_stop": "high", '
                    '"can_answer": false, "reasoning": "need more evidence"}'
                }
            )

        if url.endswith("/v2/completions"):
            return _Resp("Final synthesized answer.")

        return _Resp({"response": "ok"})

    monkeypatch.setattr("requests.post", _post)
    return _post


@pytest.fixture
def make_service(monkeypatch, tmp_path, fake_requests_post):
    """Create v3 service with trace output redirected to temp dir."""

    monkeypatch.setenv("AGENT_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("AGENTS_URL", "http://agents:8003")
    monkeypatch.setenv("AGENT_EVALUATOR_MODEL", "Qwen2.5-7B-Instruct-1M")
    monkeypatch.setenv("AGENT_INSIGHTS_MODEL", "Qwen2.5-7B-Instruct-1M")

    from api.v3.service import CompletionServiceV3

    def _factory():
        return CompletionServiceV3()

    return _factory


@pytest.fixture
def docker_env_for_tools(monkeypatch):
    """Set service URLs to docker-compose defaults for tool tests."""

    monkeypatch.setenv("AGENTS_URL", "http://agents:8003")
    monkeypatch.setenv("AGENTS_SERVICE_URL", "http://agents:8003")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-api-key")
    monkeypatch.setenv("CROSSREF_EMAIL", "tests@matprop.local")
    return {
        "AGENTS_URL": "http://agents:8003",
        "AGENTS_SERVICE_URL": "http://agents:8003",
        "SEMANTIC_SCHOLAR_API_KEY": "test-api-key",
        "CROSSREF_EMAIL": "tests@matprop.local",
    }


@pytest.fixture
def tool_test_logger(caplog):
    """Capture informative logs for comprehensive tool tests."""

    logger = logging.getLogger("tests.tools")
    caplog.set_level(logging.INFO)
    return logger
