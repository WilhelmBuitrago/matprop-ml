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

    def _post(url, json=None, headers=None, timeout=None, **kwargs):
        if url.endswith("/v2/embeddings"):
            texts = (json or {}).get("texts", [])
            vectors = []
            for text in texts:
                lowered = str(text).lower()
                vectors.append(
                    [
                        float(len(lowered.split())),
                        float("materials" in lowered),
                        float("document" in lowered),
                        float("structure" in lowered),
                    ]
                )
            return _Resp({"embeddings": vectors})

        if url.endswith("/v2/planning-evaluator"):
            mode = str((json or {}).get("mode", "")).strip().lower()
            if mode == "plan":
                tools_available = (json or {}).get("tools_available", [])
                default_tool = "query_materials_database"
                selected_tool = default_tool
                if tools_available and isinstance(tools_available[0], dict):
                    selected_tool = (
                        str(tools_available[0].get("name", default_tool)).strip()
                        or default_tool
                    )
                return _Resp(
                    {
                        "steps": [
                            {
                                "action": "use_tool",
                                "tool": selected_tool,
                                "target": "mp-149",
                                "purpose": "Collect evidence for the query",
                            }
                        ]
                    }
                )

            if mode == "evaluate":
                return _Resp(
                    {
                        "stop": True,
                        "constraints_ok": True,
                        "modify_plan": False,
                        "feedback": "enough evidence collected",
                    }
                )

            return _Resp({"steps": []})

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
    """Create completion service with trace output redirected to temp dir."""

    monkeypatch.setenv("AGENT_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("AGENTS_URL", "http://agents:8003")

    from api.v4.service import PlannedRuntimeV4Service

    def _factory():
        return PlannedRuntimeV4Service()

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


@pytest.fixture(autouse=True)
def reset_security_env(monkeypatch):
    monkeypatch.delenv("AGENT_AUTH_MODE", raising=False)
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_API_KEY_HEADER", raising=False)
    monkeypatch.delenv("AGENT_RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("AGENT_RATE_LIMIT_MAX_REQUESTS", raising=False)
    monkeypatch.delenv("AGENT_RATE_LIMIT_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)


@pytest.fixture
def tool_test_logger(caplog):
    """Capture informative logs for comprehensive tool tests."""

    logger = logging.getLogger("tests.tools")
    caplog.set_level(logging.INFO)
    return logger
