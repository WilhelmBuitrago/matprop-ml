from api.v3.loop import run_loop
from api.v3.policy import PolicyEngine
from api.v3.evaluator import Evaluator
from api.v3.state import AgentState, BudgetState
from tools.config import TOOL_REGISTRY


class _AlwaysSufficientEvaluator(Evaluator):
    def evaluate(self, state, tool_name, tool_output):
        from api.v3.state import EvaluatorFeedback

        return EvaluatorFeedback(
            sufficient=True,
            confidence=0.9,
            missing_information=[],
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

    assert out.stop_reason == "sufficient_evidence"
    assert out.execution_status == "done"


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
