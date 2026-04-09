import asyncio

from api.v4.contracts import EvaluatorFeedback, Plan, PlanStep
from api.v4.loop import run_loop
from api.v4.state import AgentState, BudgetState
from tools.config import TOOL_REGISTRY
from tools.base import ToolResult


def _patch_query_tool_success(monkeypatch):
    def _execute(_self, **_kwargs):
        return ToolResult(
            status="success",
            payload={
                "materials": [
                    {
                        "material_id": "mp-149",
                        "formula": "Si",
                        "band_gap": 1.1,
                        "density": 2.3,
                        "is_stable": True,
                        "is_metal": False,
                        "energy_above_hull": 0.0,
                        "formation_energy": -0.5,
                        "volume": 20.0,
                    }
                ],
                "count": 1,
            },
        )

    monkeypatch.setattr(
        "tools.catalog.query_materials.tool.QueryMaterialsDatabaseTool.execute",
        _execute,
    )


class _AlwaysSufficientEvaluator:
    async def evaluate(self, state):
        del state
        return EvaluatorFeedback(
            stop=True,
            constraints_ok=True,
            modify_plan=False,
            feedback="enough",
        )

    def build_history(self, state):
        del state
        return []


class _PlannerStub:
    def build_plan(self, **_kwargs):  # pragma: no cover - replanning not expected
        raise AssertionError("replanning is not expected in this scenario")


class _EmitterStub:
    async def emit(self, *_args, **_kwargs):
        return None


def test_termination_on_sufficient_evidence(monkeypatch):
    _patch_query_tool_success(monkeypatch)
    state = AgentState(
        request_id="r-term",
        query="find mp-149",
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
        budget=BudgetState(
            max_iterations=8,
            max_tool_calls=8,
            max_wall_time_ms=None,
        ),
    )
    out = asyncio.run(
        run_loop(
            state,
            TOOL_REGISTRY,
            _PlannerStub(),
            _AlwaysSufficientEvaluator(),
            _EmitterStub(),
            TOOL_REGISTRY.as_schema_catalog(),
        )
    )

    assert out.stop_reason == "sufficient_evidence"
    assert out.plan.status == "completed"


def test_termination_when_budget_exceeded_immediately(monkeypatch):
    _patch_query_tool_success(monkeypatch)
    state = AgentState(
        request_id="r-term2",
        query="find mp-149",
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
        budget=BudgetState(
            max_iterations=1,
            max_tool_calls=0,
            max_wall_time_ms=None,
        ),
    )
    out = asyncio.run(
        run_loop(
            state,
            TOOL_REGISTRY,
            _PlannerStub(),
            _AlwaysSufficientEvaluator(),
            _EmitterStub(),
            TOOL_REGISTRY.as_schema_catalog(),
        )
    )

    assert out.stop_reason == "budget_exhausted"
