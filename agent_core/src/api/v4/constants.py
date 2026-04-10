from __future__ import annotations

from typing import Final

# Canonical stop reasons for deterministic runtime control.
STOP_REASONS: Final[list[str]] = [
    "completed",
    "max_iterations",
    "max_tool_calls",
    "evaluator_failed",
    "tool_validation_failed",
    "invalid_plan",
    "timeout",
    # Transitional canonical reasons for existing control paths.
    "plan_exhausted",
    "precondition_failed",
    "planner_failed",
    "controlled_failure",
]

LEGACY_STOP_REASON_BY_CANONICAL: Final[dict[str, str]] = {
    "completed": "sufficient_evidence",
    "max_iterations": "budget_exhausted",
    "max_tool_calls": "budget_exhausted",
    "evaluator_failed": "evaluator_failed",
    "tool_validation_failed": "tool_execution_failed",
    "invalid_plan": "planner_failed",
    "timeout": "budget_exhausted",
    "plan_exhausted": "plan_exhausted",
    "precondition_failed": "precondition_failed",
    "planner_failed": "planner_failed",
    "controlled_failure": "controlled_failure",
}


def to_legacy_stop_reason(canonical: str | None) -> str | None:
    if canonical is None:
        return None
    return LEGACY_STOP_REASON_BY_CANONICAL.get(canonical, canonical)
