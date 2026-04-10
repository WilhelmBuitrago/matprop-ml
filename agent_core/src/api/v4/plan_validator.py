from __future__ import annotations

from typing import Any

from .contracts import Plan, PlanStep
from tools.base import ToolRegistry


MAX_PLAN_STEPS = 8

DEFAULT_DEPENDENCY_GRAPH: dict[str, set[str]] = {
    "document_rag": {"search_scientific_documents"},
    "validate_material_constraints": {"query_materials_database"},
}


def dependencies_satisfied(
    step: PlanStep,
    previous_steps: list[PlanStep],
    dependency_graph: dict[str, set[str]] | None = None,
) -> bool:
    graph = dependency_graph or DEFAULT_DEPENDENCY_GRAPH
    required = graph.get(step.tool, set())
    if not required:
        return True

    seen_tools = {item.tool for item in previous_steps}
    return required.issubset(seen_tools)


def validate_step_input(
    step_input: dict[str, Any], input_schema: dict[str, Any]
) -> bool:
    registry = ToolRegistry()
    ok, _ = registry._validate_against_schema(step_input, input_schema, path="$")
    return ok


def is_plan_coherent(
    plan: Plan,
    available_tools: set[str] | None = None,
    dependency_graph: dict[str, set[str]] | None = None,
) -> bool:
    if not plan.steps or len(plan.steps) > MAX_PLAN_STEPS:
        return False

    seen: set[tuple[str, str]] = set()

    for i, step in enumerate(plan.steps):
        if not step.tool.strip() or not step.purpose.strip():
            return False

        if available_tools is not None and step.tool not in available_tools:
            return False

        step_input = {
            "tool": step.tool,
            "target": step.target,
            "purpose": step.purpose,
        }
        key = (step.tool, str(step_input))
        if key in seen:
            return False
        seen.add(key)

        if not dependencies_satisfied(
            step,
            plan.steps[:i],
            dependency_graph=dependency_graph,
        ):
            return False

    return True


def build_minimal_plan(query: str, available_tools: list[dict[str, Any]]) -> Plan:
    fallback_tool = "query_materials_database"
    for item in available_tools:
        name = str(item.get("name", "")).strip()
        if name:
            fallback_tool = name
            break

    return Plan(
        steps=[
            PlanStep(
                tool=fallback_tool,
                target=query,
                purpose="Fallback minimal deterministic plan",
            )
        ],
        cursor=0,
        status="active",
    )
