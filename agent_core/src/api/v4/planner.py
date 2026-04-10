from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os
import re

import requests

from .contracts import Plan, PlanStep
from .plan_validator import (
    DEFAULT_DEPENDENCY_GRAPH,
    MAX_PLAN_STEPS,
    build_minimal_plan,
    is_plan_coherent,
    validate_step_input,
)


@dataclass(frozen=True)
class PlannerOutcome:
    plan: Plan | None
    fallback_reason: str | None = None


class DeepSeekOneShotPlanner:
    """Planner service for v4 runtime.

    This component creates plans (initial plan and optional replans) and never
    performs loop evaluation decisions.
    """

    def __init__(
        self,
        *,
        agents_url: str | None = None,
        model_name: str | None = None,
        max_steps: int = 4,
        timeout_seconds: int = 45,
    ) -> None:
        self._agents_url = (
            agents_url or os.getenv("AGENTS_URL", "http://agents:8003")
        ).rstrip("/")
        self._endpoint = f"{self._agents_url}/v2/planning-evaluator"
        self._model_name = model_name or os.getenv(
            "AGENT_PLANNING_EVALUATOR_MODEL",
            os.getenv("AGENT_PLANNER_MODEL", "deepseek-r1:8b"),
        )
        self._max_steps = min(MAX_PLAN_STEPS, max_steps)
        self._timeout_seconds = timeout_seconds

    def build_plan(
        self,
        *,
        query: str,
        tool_catalog: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
        state: dict[str, Any] | None = None,
        feedback: str | None = None,
    ) -> PlannerOutcome:
        """Build a plan from query/context without evaluating loop outcomes."""
        available_tools = {
            str(item.get("name", "")).strip()
            for item in tool_catalog
            if isinstance(item, dict)
        }

        payload = {
            "mode": "plan",
            "query": query,
            "model_name": self._model_name,
            "history": history or [],
            "tools_available": tool_catalog,
            "state": state or {},
            "plan": {},
            "execution_state": {"feedback": feedback or ""},
            "max_steps": self._max_steps,
        }

        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            parsed = response.json()
        except Exception:
            return PlannerOutcome(
                plan=build_minimal_plan(query, tool_catalog),
                fallback_reason="invalid_plan",
            )

        if not isinstance(parsed, dict):
            return PlannerOutcome(
                plan=build_minimal_plan(query, tool_catalog),
                fallback_reason="invalid_plan",
            )

        steps = self._normalize_steps(
            parsed=parsed,
            tool_catalog=tool_catalog,
            query=query,
        )
        if not steps:
            return PlannerOutcome(
                plan=build_minimal_plan(query, tool_catalog),
                fallback_reason="invalid_plan",
            )

        plan = Plan(steps=steps, cursor=0, status="active")
        if not is_plan_coherent(
            plan,
            available_tools=available_tools,
            dependency_graph=DEFAULT_DEPENDENCY_GRAPH,
        ):
            return PlannerOutcome(
                plan=build_minimal_plan(query, tool_catalog),
                fallback_reason="invalid_plan",
            )

        return PlannerOutcome(plan=plan, fallback_reason=None)

    def _normalize_steps(
        self,
        *,
        parsed: dict[str, Any],
        tool_catalog: list[dict[str, Any]],
        query: str,
    ) -> list[PlanStep]:
        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list):
            return []

        tool_definitions: dict[str, dict[str, Any]] = {
            str(item.get("name", "")).strip(): item
            for item in tool_catalog
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        }
        allowed_tools = set(tool_definitions.keys())

        normalized: list[PlanStep] = []
        for raw in raw_steps[: self._max_steps]:
            if not isinstance(raw, dict):
                continue
            action = str(raw.get("action", "use_tool")).strip().lower()
            if action == "respond":
                continue

            tool = str(raw.get("tool", "")).strip()
            if tool not in allowed_tools:
                continue

            target = raw.get("target")
            input_payload = raw.get("input", {})
            if not isinstance(input_payload, dict):
                input_payload = {}

            normalized_input = self._normalize_input_for_tool(
                tool_name=tool,
                target=target,
                input_payload=input_payload,
                query=query,
            )

            input_schema = tool_definitions.get(tool, {}).get("input_schema", {})
            if isinstance(input_schema, dict) and input_schema:
                if not validate_step_input(normalized_input, input_schema):
                    continue

            if target is None and isinstance(normalized_input, dict):
                target = (
                    normalized_input.get("material_id")
                    or normalized_input.get("formula")
                    or normalized_input.get("chemical_system")
                    or normalized_input.get("query")
                )
            purpose = str(raw.get("purpose", raw.get("reason", ""))).strip()
            if not purpose:
                purpose = f"Execute {tool}"
            normalized.append(
                PlanStep(
                    tool=tool,
                    target=str(target).strip() if target is not None else None,
                    purpose=purpose,
                )
            )

        return normalized

    def _normalize_input_for_tool(
        self,
        *,
        tool_name: str,
        target: Any,
        input_payload: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:
        if input_payload:
            return input_payload

        target_text = "" if target is None else str(target).strip()

        if tool_name == "query_materials_database":
            if target_text and re.fullmatch(
                r"mp-\d+", target_text, flags=re.IGNORECASE
            ):
                return {"material_id": target_text.lower()}
            if target_text:
                return {"formula": target_text}
            return {"formula": "Si"}

        if tool_name == "search_scientific_documents":
            return {"query": target_text or query}

        if tool_name == "document_rag":
            return {
                "documents": [
                    {
                        "document_id": "probe-doc",
                        "title": "probe",
                        "doi": None,
                        "url": None,
                        "source": "probe",
                        "relevance_score": 0.0,
                    }
                ],
                "query": target_text or query,
            }

        if tool_name == "validate_material_constraints":
            return {"constraints": {"is_stable": True}}

        if tool_name == "generate_crystal_structure":
            return {"query": target_text or query}

        return {}
