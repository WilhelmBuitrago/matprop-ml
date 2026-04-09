from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

import requests

from .contracts import Plan, PlanStep


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
        self._max_steps = max_steps
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
            return PlannerOutcome(plan=None, fallback_reason="planner_request_failed")

        if not isinstance(parsed, dict):
            return PlannerOutcome(plan=None, fallback_reason="planner_invalid_payload")

        steps = self._normalize_steps(parsed=parsed, tool_catalog=tool_catalog)
        if not steps:
            return PlannerOutcome(
                plan=None, fallback_reason="planner_empty_after_filter"
            )

        plan = Plan(steps=steps, cursor=0, status="active")
        if not is_plan_coherent(plan):
            return PlannerOutcome(plan=None, fallback_reason="planner_incoherent")

        return PlannerOutcome(plan=plan, fallback_reason=None)

    def _normalize_steps(
        self,
        *,
        parsed: dict[str, Any],
        tool_catalog: list[dict[str, Any]],
    ) -> list[PlanStep]:
        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list):
            return []

        allowed_tools = {
            str(item.get("name", "")).strip()
            for item in tool_catalog
            if isinstance(item, dict)
        }

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
            if target is None and isinstance(raw.get("input"), dict):
                input_payload = raw.get("input", {})
                target = (
                    input_payload.get("material_id")
                    or input_payload.get("formula")
                    or input_payload.get("query")
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


def is_plan_coherent(plan: Plan) -> bool:
    if not plan.steps:
        return False

    seen_doc_search = False
    previous_tool = ""

    for step in plan.steps:
        if not step.tool.strip() or not step.purpose.strip():
            return False
        if previous_tool and previous_tool == step.tool:
            return False
        if step.tool == "search_scientific_documents":
            seen_doc_search = True
        if step.tool == "document_rag" and not seen_doc_search:
            return False
        previous_tool = step.tool

    return True
