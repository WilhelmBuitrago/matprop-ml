from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import os

import requests

from .contracts import Plan, PlanStep


@dataclass(frozen=True)
class PlannerOutcome:
    plan: Plan | None
    fallback_reason: str | None = None


class DeepSeekOneShotPlanner:
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
        self._endpoint = f"{self._agents_url}/v2/completions"
        self._model_name = model_name or os.getenv(
            "AGENT_PLANNER_MODEL", "deepseek-r1:8b"
        )
        self._max_steps = max_steps
        self._timeout_seconds = timeout_seconds

    def build_plan(
        self,
        *,
        query: str,
        tool_catalog: list[dict[str, Any]],
    ) -> PlannerOutcome:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a scientific planning agent specialized in materials science. "
                    "Generate a minimal, efficient sequence of tool calls. "
                    "Only use tools from the provided catalog. "
                    "Return only valid JSON, no explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\\n\\n"
                    f"Available tools:\\n{self._format_tool_catalog(tool_catalog)}\\n\\n"
                    'Return JSON: {"steps": [{"tool": "...", "target": "...", "purpose": "..."}]}'
                ),
            },
        ]

        payload = {
            "history": messages,
            "model_name": self._model_name,
            "temperature": 0.1,
            "max_tokens": 512,
        }

        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            raw_text = self._extract_model_text(response.json())
        except Exception:
            return PlannerOutcome(plan=None, fallback_reason="planner_request_failed")

        parsed = self._parse_json_object(raw_text)
        if parsed is None:
            return PlannerOutcome(plan=None, fallback_reason="planner_invalid_json")

        steps = self._normalize_steps(parsed=parsed, tool_catalog=tool_catalog)
        if not steps:
            return PlannerOutcome(
                plan=None, fallback_reason="planner_empty_after_filter"
            )

        plan = Plan(steps=steps, cursor=0, status="active")
        if not is_plan_coherent(plan):
            return PlannerOutcome(plan=None, fallback_reason="planner_incoherent")

        return PlannerOutcome(plan=plan, fallback_reason=None)

    def _format_tool_catalog(self, tool_catalog: list[dict[str, Any]]) -> str:
        compact = [
            {
                "name": str(item.get("name", "")).strip(),
                "description": str(item.get("description", "")).strip(),
            }
            for item in tool_catalog
            if isinstance(item, dict)
        ]
        return json.dumps(compact, ensure_ascii=True)

    def _extract_model_text(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("response"), str):
                return payload["response"]
            return payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        return str(payload or "")

    def _parse_json_object(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                return None
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

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
            tool = str(raw.get("tool", "")).strip()
            if tool not in allowed_tools:
                continue
            target = raw.get("target")
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
