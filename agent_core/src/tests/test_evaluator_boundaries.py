from api.v4.contracts import Plan, PlanStep
from api.v4.evaluator import LoopEvaluatorV4
from api.v4.state import AgentState, BudgetState
from api.v4.trace import TraceEntry


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
