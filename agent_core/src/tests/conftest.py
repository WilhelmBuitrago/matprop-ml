import os
import sys
from typing import Any, Dict

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
        if (
            url.endswith("/v1/completions")
            and json
            and "strict json" in str(json).lower()
        ):
            return _Resp(
                {
                    "response": '{"sufficient": false, "confidence": 0.65, '
                    '"missing_information": ["comparison"], "reasoning": "need more evidence"}'
                }
            )

        if url.endswith("/v1/completions"):
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
