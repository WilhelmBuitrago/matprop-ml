from api.v3.evaluator import Evaluator
from api.v3.state import AgentState, BudgetState


def test_evaluator_returns_structured_suggestions_only(fake_requests_post):
    evaluator = Evaluator()
    state = AgentState(
        request_id="r-eval",
        query="find best semiconductor",
        intent="material_lookup",
        budget=BudgetState(),
    )

    feedback = evaluator.evaluate(
        state=state,
        tool_name="query_materials_database",
        tool_output={"materials": [], "count": 0},
        next_planned_step="compare_materials",
        tools_available=["query_materials_database", "compare_materials"],
    )

    assert feedback.verdict in {"sufficient", "insufficient"}
    assert 0.0 <= feedback.confidence <= 1.0
    assert isinstance(feedback.missing_information, list)
    assert feedback.risk_if_stop in {"low", "medium", "high"}
    assert isinstance(feedback.can_answer, bool)
    assert feedback.reasoning
