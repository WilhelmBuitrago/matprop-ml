from __future__ import annotations

from typing import Any
import asyncio
import json
import os

import requests

from .contracts import EvaluatorFeedback, PlanChange, validate_plan_changes
from .state import AgentState


EVALUATOR_SYSTEM_PROMPT = (
    "You are a strict evaluator for a scientific tool-execution loop. "
    "Decide if we should stop and if the plan should be modified. "
    "Return strict JSON only with keys: stop, modify_plan, suggested_changes, confidence, risk, trace. "
    "risk must be one of: low, medium, high. suggested_changes must be an array of PlanChange objects "
    "with fields: action(insert|remove|replace), index(integer), step(optional object with tool,target,purpose)."
)


class LoopEvaluatorV4:
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
        self._endpoint = f"{self._agents_url}/v2/completions"
        self._model_name = model_name or os.getenv(
            "AGENT_EVALUATOR_MODEL",
            "yasserrmd/Qwen2.5-7B-Instruct-1M",
        )
        self._timeout_seconds = timeout_seconds

    async def evaluate(self, state: AgentState) -> EvaluatorFeedback:
        return await asyncio.to_thread(self._evaluate_sync, state)

    def _evaluate_sync(self, state: AgentState) -> EvaluatorFeedback:
        fallback = self._fallback_feedback(state)
        messages = self._build_messages(state)

        payload = {
            "history": messages,
            "model_name": self._model_name,
            "temperature": 0.1,
            "max_tokens": 420,
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
            parsed = self._parse_json(raw_text)
            if parsed is None:
                return fallback
            return self._coerce_feedback(parsed, state)
        except Exception:
            return fallback

    def _build_messages(self, state: AgentState) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
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
                            {"tool_call": entry.payload}, ensure_ascii=True
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

    def _extract_model_text(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("response"), str):
                return payload["response"]
            return payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        return str(payload or "")

    def _parse_json(self, text: str) -> dict[str, Any] | None:
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

    def _coerce_feedback(
        self, parsed: dict[str, Any], state: AgentState
    ) -> EvaluatorFeedback:
        raw_changes = parsed.get("suggested_changes", [])
        changes: list[PlanChange] = []
        if isinstance(raw_changes, list):
            try:
                changes = validate_plan_changes(raw_changes)
            except Exception:
                changes = []

        risk = str(parsed.get("risk", "medium")).strip().lower()
        if risk not in {"low", "medium", "high"}:
            risk = "medium"

        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        feedback = EvaluatorFeedback(
            stop=bool(parsed.get("stop", False)),
            modify_plan=bool(parsed.get("modify_plan", False)),
            suggested_changes=changes,
            confidence=confidence,
            risk=risk,
            trace=str(parsed.get("trace", "")).strip() or "evaluation_complete",
        )

        if feedback.modify_plan and not feedback.suggested_changes:
            return feedback.model_copy(update={"modify_plan": False})

        return feedback

    def _fallback_feedback(self, state: AgentState) -> EvaluatorFeedback:
        has_evidence = bool(state.hypotheses or state.constraints.get("documents"))
        near_plan_end = state.plan.cursor >= max(0, len(state.plan.steps) - 1)
        if has_evidence and near_plan_end:
            return EvaluatorFeedback(
                stop=True,
                modify_plan=False,
                suggested_changes=[],
                confidence=0.7,
                risk="low",
                trace="fallback_evaluator_sufficient",
            )

        return EvaluatorFeedback(
            stop=False,
            modify_plan=False,
            suggested_changes=[],
            confidence=0.45,
            risk="medium",
            trace="fallback_evaluator_continue",
        )
