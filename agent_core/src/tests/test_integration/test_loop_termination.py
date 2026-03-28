from api.v3.loop import run_loop
from api.v3.policy import PolicyEngine
from api.v3.evaluator import Evaluator
from api.v3.state import AgentState, BudgetState
from tools.config import TOOL_REGISTRY


class _AlwaysSufficientEvaluator(Evaluator):
    def evaluate(
        self,
        state,
        tool_name,
        tool_output,
        next_planned_step,
        tools_available,
    ):
        from api.v3.state import EvaluatorFeedback

        return EvaluatorFeedback(
            verdict="sufficient",
            confidence=0.9,
            missing_information=[],
            risk_if_stop="low",
            can_answer=True,
            reasoning="enough",
        )


def test_termination_on_sufficient_evidence():
    state = AgentState(
        request_id="r-term",
        query="find mp-149",
        intent="material_lookup",
        budget=BudgetState(
            max_iterations=8,
            max_tool_calls=8,
            max_context_tokens=2048,
            max_wall_time_ms=30000,
        ),
    )
    out = run_loop(state, PolicyEngine(), _AlwaysSufficientEvaluator(), TOOL_REGISTRY)

    last_trace = out.policy_trace[-1] if out.policy_trace else {}
    assert (
        out.stop_reason == "sufficient_evidence"
    ), f"unexpected stop_reason={out.stop_reason}; last_policy_trace={last_trace}"
    assert out.execution_status == "done"
    assert out.evaluation_trace
    assert out.evaluation_trace[-1]["eval"]["can_answer"] is True


def test_termination_when_budget_exceeded_immediately():
    state = AgentState(
        request_id="r-term2",
        query="find mp-149",
        intent="material_lookup",
        budget=BudgetState(
            max_iterations=1,
            max_tool_calls=0,
            max_context_tokens=2048,
            max_wall_time_ms=30000,
        ),
    )
    out = run_loop(state, PolicyEngine(), _AlwaysSufficientEvaluator(), TOOL_REGISTRY)

    assert out.stop_reason in {"max_tool_calls", "budget_exhausted"}
