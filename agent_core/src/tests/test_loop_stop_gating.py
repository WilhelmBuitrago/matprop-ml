from api.v4.contracts import EvaluatorFeedback as EvaluatorFeedbackV4, Plan, PlanStep
from api.v4.loop import run_loop as run_loop_v4
from api.v4.state import AgentState as AgentStateV4, BudgetState as BudgetStateV4
from tools.base import ToolResult


class _ToolStub:
    name = "query_materials_database"
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}

    def execute(self, **_kwargs):
        return ToolResult(status="success", payload={"materials": [], "count": 0})


class _RegistryStub:
    def __init__(self):
        self._tool = _ToolStub()

    def can_run(self, _tool_name, _state):
        return True

    def validate_input(self, _tool_name, _arguments):
        return True, ""

    def validate_output(self, _tool_name, _payload):
        return True, ""

    def get(self, _tool_name):
        return self._tool


class _PlannerStub:
    def build_plan(self, **_kwargs):  # pragma: no cover - not used in these tests
        raise AssertionError("replanning is not expected in this scenario")


class _EvaluatorStub:
    def __init__(self, feedback: EvaluatorFeedbackV4):
        self._feedback = feedback

    async def evaluate(self, _state):
        return self._feedback

    def build_history(self, _state):
        return []


class _EmitterStub:
    def __init__(self):
        self.events = []

    async def emit(self, event, payload, **kwargs):
        self.events.append((event, payload, kwargs))


def _should_stop(feedback: EvaluatorFeedbackV4) -> bool:
    return feedback.stop and feedback.constraints_ok


def test_v4_stop_gating_requires_constraints_ok():
    assert (
        _should_stop(
            EvaluatorFeedbackV4(
                stop=True,
                constraints_ok=False,
                modify_plan=False,
                feedback="missing constraints",
            )
        )
        is False
    )
    assert (
        _should_stop(
            EvaluatorFeedbackV4(
                stop=True,
                constraints_ok=True,
                modify_plan=False,
                feedback="enough evidence",
            )
        )
        is True
    )


def _build_v4_state() -> AgentStateV4:
    return AgentStateV4(
        request_id="v4-stop",
        query="find mp-149",
        plan=Plan(
            steps=[
                PlanStep(
                    tool="query_materials_database",
                    target="mp-149",
                    purpose="Collect materials evidence",
                )
            ],
            cursor=0,
            status="active",
        ),
        budget=BudgetStateV4(max_iterations=2, max_tool_calls=2, max_wall_time_ms=None),
    )


def test_v4_does_not_stop_without_constraints_ok():
    import asyncio

    state = _build_v4_state()
    evaluator = _EvaluatorStub(
        EvaluatorFeedbackV4(
            stop=True,
            constraints_ok=False,
            modify_plan=False,
            feedback="constraints are incomplete",
        )
    )

    out = asyncio.run(
        run_loop_v4(
            state,
            _RegistryStub(),
            _PlannerStub(),
            evaluator,
            _EmitterStub(),
            [{"name": "query_materials_database", "description": "query"}],
        )
    )

    assert out.stop_reason != "sufficient_evidence"
    assert out.stop_reason == "plan_exhausted"


def test_v4_stops_when_constraints_ok_is_true():
    import asyncio

    state = _build_v4_state()
    evaluator = _EvaluatorStub(
        EvaluatorFeedbackV4(
            stop=True,
            constraints_ok=True,
            modify_plan=False,
            feedback="enough evidence",
        )
    )

    out = asyncio.run(
        run_loop_v4(
            state,
            _RegistryStub(),
            _PlannerStub(),
            evaluator,
            _EmitterStub(),
            [{"name": "query_materials_database", "description": "query"}],
        )
    )

    assert out.stop_reason == "sufficient_evidence"


def test_v4_domain_invalid_never_stops_even_if_evaluator_requests_stop():
    import asyncio

    state = _build_v4_state()
    state.replans_used = 2
    state.sync_execution_state()
    evaluator = _EvaluatorStub(
        EvaluatorFeedbackV4(
            stop=True,
            constraints_ok=True,
            modify_plan=False,
            feedback="enough evidence",
            domain_valid=False,
            domain_confidence=0.2,
            domain_issues=["physical inconsistency"],
        )
    )

    out = asyncio.run(
        run_loop_v4(
            state,
            _RegistryStub(),
            _PlannerStub(),
            evaluator,
            _EmitterStub(),
            [{"name": "query_materials_database", "description": "query"}],
        )
    )

    assert out.stop_reason != "sufficient_evidence"
    assert out.stop_reason == "plan_exhausted"
