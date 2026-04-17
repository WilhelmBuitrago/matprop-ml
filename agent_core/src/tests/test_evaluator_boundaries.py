from api.v4.contracts import Plan, PlanStep
from api.v4.evaluator import LoopEvaluatorV4
from api.v4.state import AgentState, BudgetState
from api.v4.trace import TraceEntry
import pytest


def test_v4_evaluator_returns_structured_feedback(fake_requests_post):
    import asyncio

    evaluator = LoopEvaluatorV4()
    state = AgentState(
        request_id="r-eval-v4-structured",
        query="find best semiconductor",
        plan=Plan(
            steps=[
                PlanStep(
                    tool="query_materials_database",
                    target="mp-149",
                    purpose="Collect evidence",
                )
            ],
            cursor=0,
            status="active",
        ),
        budget=BudgetState(max_iterations=4, max_tool_calls=4, max_wall_time_ms=None),
    )

    feedback = asyncio.run(evaluator.evaluate(state))

    assert isinstance(feedback.stop, bool)
    assert isinstance(feedback.constraints_ok, bool)
    assert isinstance(feedback.modify_plan, bool)
    assert isinstance(feedback.feedback, str)
    assert feedback.feedback


def test_v4_evaluator_history_uses_only_valid_roles_and_no_side_effects():
    evaluator = LoopEvaluatorV4()
    state = AgentState(
        request_id="r-eval-v4",
        query="find best semiconductor",
        plan=Plan(
            steps=[
                PlanStep(
                    tool="query_materials_database",
                    target="mp-149",
                    purpose="Collect evidence",
                )
            ],
            cursor=0,
            status="active",
        ),
        budget=BudgetState(max_iterations=4, max_tool_calls=4, max_wall_time_ms=None),
    )

    state.execution_trace.append(
        TraceEntry(
            iteration=1,
            event="tool_start",
            payload={"tool": "query_materials_database"},
            trace_model="tool start",
        )
    )
    state.execution_trace.append(
        TraceEntry(
            iteration=1,
            event="tool_result",
            payload={"status": "success"},
            trace_model="tool result",
        )
    )

    before = list(state.execution_trace)
    history = evaluator.build_history(state)

    assert state.execution_trace == before
    assert history
    assert {item["role"] for item in history}.issubset(
        {"system", "user", "assistant", "tool"}
    )
    assert all(item["role"] != "evaluator" for item in history)


def test_v4_domain_critic_invalid_forces_replan(monkeypatch):
    import asyncio

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    calls = {"domain_critic": 0}

    def _post(url, json=None, headers=None, timeout=None, **kwargs):
        del json, headers, timeout, kwargs
        if url.endswith("/v2/planning-evaluator"):
            return _Resp(
                {
                    "stop": True,
                    "constraints_ok": True,
                    "modify_plan": False,
                    "feedback": "enough evidence",
                    "confidence": 0.89,
                }
            )
        if url.endswith("/v2/domain-critic"):
            calls["domain_critic"] += 1
            return _Resp(
                {
                    "response": "VALID: no\nCONFIDENCE: 0.2\nISSUES:\n- physical inconsistency"
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("requests.post", _post)

    evaluator = LoopEvaluatorV4(domain_critic_mode="always")
    state = AgentState(
        request_id="r-eval-v4-domain-invalid",
        query="find stable Si with unrealistic lattice value",
        plan=Plan(
            steps=[
                PlanStep(
                    tool="query_materials_database",
                    target="mp-149",
                    purpose="Collect evidence",
                )
            ],
            cursor=0,
            status="active",
        ),
        budget=BudgetState(max_iterations=4, max_tool_calls=4, max_wall_time_ms=None),
    )

    feedback = asyncio.run(evaluator.evaluate(state))

    assert feedback.stop is False
    assert feedback.modify_plan is True
    assert feedback.domain_valid is False
    assert feedback.domain_issues == ["physical inconsistency"]
    assert feedback.confidence == pytest.approx(0.2)
    assert calls["domain_critic"] == 1


def test_v4_domain_critic_only_stop_skips_call_when_not_stopping(monkeypatch):
    import asyncio

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    calls = {"domain_critic": 0}

    def _post(url, json=None, headers=None, timeout=None, **kwargs):
        del json, headers, timeout, kwargs
        if url.endswith("/v2/planning-evaluator"):
            return _Resp(
                {
                    "stop": False,
                    "constraints_ok": False,
                    "modify_plan": False,
                    "feedback": "continue",
                    "confidence": 0.61,
                }
            )
        if url.endswith("/v2/domain-critic"):
            calls["domain_critic"] += 1
            return _Resp(
                {
                    "response": "VALID: yes\nCONFIDENCE: 0.9\nISSUES:\n- none"
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("requests.post", _post)

    evaluator = LoopEvaluatorV4(domain_critic_mode="only_stop")
    state = AgentState(
        request_id="r-eval-v4-domain-only-stop",
        query="find best semiconductor",
        plan=Plan(
            steps=[
                PlanStep(
                    tool="query_materials_database",
                    target="mp-149",
                    purpose="Collect evidence",
                )
            ],
            cursor=0,
            status="active",
        ),
        budget=BudgetState(max_iterations=4, max_tool_calls=4, max_wall_time_ms=None),
    )

    feedback = asyncio.run(evaluator.evaluate(state))

    assert feedback.stop is False
    assert feedback.modify_plan is False
    assert feedback.domain_valid is True
    assert feedback.domain_issues == []
    assert calls["domain_critic"] == 0
