from __future__ import annotations

from typing import Any
import asyncio
import json
import os

import requests

from .contracts import EvaluatorFeedback
from .state import AgentState


EVALUATOR_SYSTEM_MESSAGE = (
    "You are an external evaluator controller. "
    "You are not a conversational actor and must not produce user-facing answers."
)


class LoopEvaluatorV4:
    """Loop-only evaluator service.

    Evaluator is invoked after each tool execution inside the runtime loop and
    does not evaluate the entry-policy planning stage.
    """

    def __init__(
        self,
        *,
        agents_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int = 45,
    ) -> None:
        self._agents_url = (
            agents_url or os.getenv("AGENTS_URL", "http://agents:8003")
        ).rstrip("/")
        self._endpoint = f"{self._agents_url}/v2/planning-evaluator"
        self._model_name = model_name or os.getenv(
            "AGENT_PLANNING_EVALUATOR_MODEL",
            os.getenv("AGENT_EVALUATOR_MODEL", "deepseek-r1:8b"),
        )
        self._timeout_seconds = timeout_seconds

    async def evaluate(self, state: AgentState) -> EvaluatorFeedback:
        """Evaluate current loop state and return control feedback."""
        return await asyncio.to_thread(self._evaluate_sync, state)

    def _evaluate_sync(self, state: AgentState) -> EvaluatorFeedback:
        payload = {
            "mode": "evaluate",
            "query": state.query,
            "model_name": self._model_name,
            "history": self.build_history(state),
            "tools_available": [],
            "state": self._state_snapshot(state),
            "plan": state.plan.model_dump(),
            "execution_state": {
                "iterations_used": state.budget.iterations_used,
                "tool_calls_used": state.budget.tool_calls_used,
                "replans_used": state.replans_used,
            },
            "max_steps": max(1, len(state.plan.steps)),
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
            if not isinstance(parsed, dict):
                raise RuntimeError("evaluator_invalid_payload")
            feedback = str(parsed.get("feedback", "")).strip()
            constraints_ok = bool(
                parsed.get("constraints_ok", parsed.get("stop", False))
            )
            return EvaluatorFeedback(
                stop=bool(parsed.get("stop", False)),
                constraints_ok=constraints_ok,
                modify_plan=bool(parsed.get("modify_plan", False)),
                feedback=feedback or "continue_with_current_plan",
            )
        except Exception as exc:
            raise RuntimeError(f"evaluator_failed: {exc}") from exc

    def build_history(self, state: AgentState) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": EVALUATOR_SYSTEM_MESSAGE},
            {"role": "user", "content": state.query},
            {
                "role": "assistant",
                "content": json.dumps(
                    {"plan": state.plan.model_dump()}, ensure_ascii=True
                ),
            },
        ]

        for entry in state.execution_trace:
            if entry.event == "tool_start":
                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {"action": "use_tool", "tool_call": entry.payload},
                            ensure_ascii=True,
                        ),
                    }
                )
            elif entry.event == "tool_result":
                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            {"tool_result": entry.payload}, ensure_ascii=True
                        ),
                    }
                )

        return messages

    def _state_snapshot(self, state: AgentState) -> dict[str, Any]:
        return {
            "materials_count": len(state.hypotheses),
            "documents_count": len(state.documents),
            "insights_count": len(state.extracted_insights),
            "plan_cursor": state.plan.cursor,
            "plan_steps": len(state.plan.steps),
            "stop_reason": state.stop_reason,
        }
