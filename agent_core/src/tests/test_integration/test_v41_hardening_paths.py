from __future__ import annotations

from api.v4.contracts import EvaluationResult, PlanStep
from api.v4.scheme import CompletionRequestV4


def test_v41_valid_plan_completes(make_service):
    service = make_service()

    response = service.chat(
        CompletionRequestV4(
            query="find material mp-149 and summarize",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.metadata["stop_reason"] in {
        "sufficient_evidence",
        "plan_exhausted",
        "budget_exhausted",
    }
    assert response.metadata["stop_reason_canonical"] in {
        "completed",
        "plan_exhausted",
        "max_iterations",
        "max_tool_calls",
    }


def test_v41_invalid_plan_fallback_to_minimal(make_service):
    service = make_service()

    def _normalize_steps_invalid(*_args, **_kwargs):
        return []

    service.runtime.planner._normalize_steps = _normalize_steps_invalid

    response = service.chat(
        CompletionRequestV4(
            query="find silicon candidates",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.metadata["planner_status"] == "failed"
    assert response.metadata["planner_fallback_reason"] == "invalid_plan"


def test_v41_evaluator_failure_has_deterministic_fallback(make_service):
    service = make_service()

    async def _raise(_state):
        raise RuntimeError("forced evaluator failure")

    service.runtime.evaluator.evaluate = _raise

    response = service.chat(
        CompletionRequestV4(
            query="find mp-149 with strict constraints",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.metadata["stop_reason"] == "evaluator_failed"
    assert response.metadata["stop_reason_canonical"] == "evaluator_failed"
    assert isinstance(response.choices[0]["text"], str)


def test_v41_tool_failure_maps_to_validation_stop(make_service, monkeypatch):
    service = make_service()
    from tools.config import TOOL_REGISTRY

    monkeypatch.setattr(
        TOOL_REGISTRY,
        "validate_output",
        lambda *_args, **_kwargs: (False, "forced output validation error"),
    )

    response = service.chat(
        CompletionRequestV4(
            query="find mp-149",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.metadata["stop_reason"] == "tool_execution_failed"
    assert response.metadata["stop_reason_canonical"] == "tool_validation_failed"


def test_v41_max_iterations_enforced(make_service):
    service = make_service()

    async def _never_stop(_state):
        return EvaluationResult(
            stop=False,
            modify_plan=False,
            constraints_ok=False,
            reason="continue",
        )

    service.runtime.evaluator.evaluate = _never_stop
    service.runtime.planner._normalize_steps = lambda *args, **kwargs: [
        PlanStep(
            tool="query_materials_database",
            target="mp-149",
            purpose="step-1",
        ),
        PlanStep(
            tool="search_scientific_documents",
            target="Si",
            purpose="step-2",
        ),
    ]

    response = service.chat(
        CompletionRequestV4(
            query="find mp-149",
            max_iterations=1,
            max_tool_calls=8,
        )
    )

    assert response.metadata["stop_reason"] == "budget_exhausted"
    assert response.metadata["stop_reason_canonical"] == "max_iterations"
