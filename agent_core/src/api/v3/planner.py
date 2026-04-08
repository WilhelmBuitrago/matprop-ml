from __future__ import annotations

import os
from typing import Any, Dict, List

import requests


class QwenPlanner:
    """One-shot planner client that delegates planning to agents service."""

    def __init__(
        self,
        model_url: str | None = None,
        max_steps: int = 3,
    ):
        self.model_url = (
            model_url or os.getenv("AGENTS_URL", "http://agents:8003")
        ).rstrip("/")
        self.max_steps = max_steps
        self.endpoint = f"{self.model_url}/v2/planner"

    def build_plan(
        self,
        *,
        query: str,
        state: Dict[str, Any],
        candidate_tools: List[Dict[str, Any]],
        retry_once: bool = True,
    ) -> Dict[str, Any]:
        attempts = 2 if retry_once else 1
        last_error: Exception | None = None

        for _ in range(attempts):
            try:
                return self._build_plan_once(
                    query=query,
                    state=state,
                    candidate_tools=candidate_tools,
                )
            except ValueError as exc:
                last_error = exc

        if last_error is not None:
            raise ValueError(
                f"Planner output is invalid JSON: {last_error}"
            ) from last_error
        raise ValueError("Planner output is invalid JSON")

    def _build_plan_once(
        self,
        *,
        query: str,
        state: Dict[str, Any],
        candidate_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload = {
            "query": query,
            "state": state,
            "candidate_tools": candidate_tools,
            "max_steps": self.max_steps,
        }

        response = requests.post(
            self.endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ValueError("Planner endpoint did not return a JSON object")

        if "steps" not in parsed:
            raise ValueError("Planner endpoint response missing 'steps'")

        return self._normalize_plan(parsed, candidate_tools=candidate_tools)

    def _normalize_plan(
        self,
        parsed: Dict[str, Any],
        *,
        candidate_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        allowed = {
            str(item.get("name", "")).strip()
            for item in candidate_tools
            if isinstance(item, dict)
        }

        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("'steps' must be a list")

        normalized_steps: List[Dict[str, str]] = []
        for step in raw_steps[: self.max_steps]:
            if not isinstance(step, dict):
                continue
            tool = str(step.get("tool", "")).strip()
            reason = str(step.get("reason", "")).strip()
            if not tool or tool not in allowed:
                continue
            normalized_steps.append({"tool": tool, "reason": reason})

        if not normalized_steps:
            raise ValueError("planner returned zero valid steps")

        return {"steps": normalized_steps}
