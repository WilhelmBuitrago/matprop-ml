from __future__ import annotations

from typing import Any
import asyncio
import json
import logging
import os

import requests

from .contracts import EvaluationResult
from .history_item import HistoryItem
from .state import AgentState
from .truncation import truncate_history


EVALUATOR_SYSTEM_MESSAGE = (
    "You are an external evaluator controller. "
    "You are not a conversational actor and must not produce user-facing answers."
)

logger = logging.getLogger(__name__)


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
        max_history_tokens: int | None = None,
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
        self._max_history_tokens = int(
            max_history_tokens
            if max_history_tokens is not None
            else os.getenv("AGENT_HISTORY_MAX_TOKENS", "2048")
        )

    async def evaluate(self, state: AgentState) -> EvaluationResult:
        """Evaluate current loop state and return control feedback."""
        return await asyncio.to_thread(self._evaluate_sync, state)

    def _evaluate_sync(self, state: AgentState) -> EvaluationResult:
        logger.info(
            "evaluator_start request_id=%s cursor=%d",
            state.request_id,
            state.plan.cursor,
        )
        state.sync_execution_state()
        state.refresh_runtime_counts()

        execution_state_payload = {}
        if state.execution_state is not None:
            execution_state_payload = state.execution_state.to_dict()

        payload = {
            "mode": "evaluate",
            "query": state.query,
            "model_name": self._model_name,
            "history": self.build_history(state),
            "tools_available": [],
            "state": self._state_snapshot(state),
            "plan": state.plan.model_dump(),
            "execution_state": execution_state_payload,
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
            return EvaluationResult(
                stop=bool(parsed.get("stop", False)),
                modify_plan=bool(parsed.get("modify_plan", False)),
                constraints_ok=constraints_ok,
                reason=feedback or "continue_with_current_plan",
            )
        except Exception as exc:
            logger.exception("evaluator_failed request_id=%s", state.request_id)
            raise RuntimeError(f"evaluator_failed: {exc}") from exc

    def build_history(self, state: AgentState) -> list[dict[str, str]]:
        items = self.build_history_items(state)
        truncated = truncate_history(items, max_tokens=self._max_history_tokens)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": EVALUATOR_SYSTEM_MESSAGE},
        ]
        for item in truncated:
            content = str(item.content or "").strip()
            if not content and item.metadata:
                content = json.dumps(item.metadata, ensure_ascii=True)
            if item.role not in {"user", "assistant", "tool"}:
                continue
            if not content:
                continue
            messages.append({"role": item.role, "content": content})

        return messages

    def build_history_items(self, state: AgentState) -> list[HistoryItem]:
        if state.history:
            return list(state.history)

        items: list[HistoryItem] = [
            HistoryItem(role="user", type="query", content=state.query),
            HistoryItem(
                role="assistant",
                type="plan",
                content=json.dumps(
                    {"plan": state.plan.model_dump()}, ensure_ascii=True
                ),
                metadata={"plan": state.plan.model_dump()},
            ),
        ]

        for entry in state.execution_trace:
            if entry.event == "tool_start":
                payload = {"action": "use_tool", "tool_call": entry.payload}
                items.append(
                    HistoryItem(
                        role="assistant",
                        type="tool_call",
                        content=json.dumps(payload, ensure_ascii=True),
                        metadata=payload,
                    )
                )
            elif entry.event == "tool_result":
                payload = {"tool_result": entry.payload}
                items.append(
                    HistoryItem(
                        role="tool",
                        type="tool_result",
                        content=json.dumps(payload, ensure_ascii=True),
                        metadata=payload,
                    )
                )

        return items

    def _state_snapshot(self, state: AgentState) -> dict[str, Any]:
        state.refresh_runtime_counts()
        runtime_state = state.runtime_state.to_dict() if state.runtime_state else {}
        return {
            "materials_count": runtime_state.get(
                "materials_count", len(state.hypotheses)
            ),
            "documents_count": runtime_state.get(
                "documents_count", len(state.documents)
            ),
            "insights_count": runtime_state.get(
                "insights_count", len(state.extracted_insights)
            ),
            "plan_cursor": runtime_state.get("plan_cursor", state.plan.cursor),
            "plan_steps": len(state.plan.steps),
            "stop_reason": state.stop_reason_canonical or state.stop_reason,
        }
