from __future__ import annotations

from typing import Any, Dict, List
import json
import os
import requests

from .model_io import clean_model_response, extract_model_text, messages_to_history
from .state import AgentState, EvaluatorFeedback


class Evaluator:
    """Model-driven evaluator that only emits sufficiency signals and gaps.

    Model choice:
    - Qwen2.5-7B-Instruct-1M is selected because evaluator prompts may include
      large aggregated tool outputs and document snippets requiring long context.
    - This evaluator does not choose actions and cannot override deterministic policy.
    """

    def __init__(self, model_url: str | None = None, model_name: str | None = None):
        self.model_url = model_url or os.getenv("AGENTS_URL", "http://agents:8003")
        self.model_name = model_name or os.getenv(
            "AGENT_EVALUATOR_MODEL", "Qwen2.5-7B-Instruct-1M"
        )

    def evaluate(
        self,
        state: AgentState,
        tool_name: str,
        tool_output: Dict[str, Any],
        next_planned_step: str,
        tools_available: List[str],
    ) -> EvaluatorFeedback:
        """Evaluate evidence quality without controlling loop behavior."""
        prompt = self._build_prompt(
            state=state,
            tool_name=tool_name,
            tool_output=tool_output,
            next_planned_step=next_planned_step,
            tools_available=tools_available,
        )
        fallback = EvaluatorFeedback(
            verdict="insufficient",
            confidence=0.4,
            missing_information=["additional_evidence"],
            risk_if_stop="high",
            can_answer=False,
            reasoning="fallback_evaluation",
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "history": messages_to_history(messages),
                "temperature": 0.1,
                "max_tokens": 300,
            }
            response = requests.post(
                f"{self.model_url}/v2/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            text = clean_model_response(extract_model_text(response.json()))
            parsed = self._parse_json(text)
            return self._coerce_feedback(parsed)
        except Exception:
            return fallback

    def _build_prompt(
        self,
        state: AgentState,
        tool_name: str,
        tool_output: Dict[str, Any],
        next_planned_step: str,
        tools_available: List[str],
    ) -> str:
        """Construct strict JSON-only evaluator prompt."""
        latest_materials = [m.material_id for m in state.materials_found[:5]]
        latest_docs = [d.title for d in state.documents[:5]]
        executed_steps = [
            {
                "tool": step.get("tool_name", ""),
                "reasoning": step.get("reasoning", ""),
            }
            for step in state.policy_trace[-8:]
        ]
        current_state = {
            "materials_count": len(state.materials_found),
            "documents_count": len(state.documents),
            "insights_count": len(state.extracted_insights),
            "has_comparison": bool(state.properties_collected.get("comparison")),
            "has_constraint_validation": bool(
                state.properties_collected.get("constraint_validation")
            ),
            "has_document_rag": bool(
                state.properties_collected.get("document_rag_results")
            ),
            "known_material_ids": latest_materials,
            "known_document_titles": latest_docs,
            "collected_properties": sorted(state.properties_collected.keys())[:20],
        }
        evaluator_input = {
            "query": state.query,
            "current_state": current_state,
            "executed_steps": executed_steps,
            "next_planned_step": next_planned_step,
            "tools_available": tools_available,
            "last_tool_name": tool_name,
            "last_tool_output": tool_output,
        }
        return (
            "You are a strict evaluator, not a planner.\\n"
            "Evaluate if the system can produce a correct and complete final answer IF IT STOPS NOW.\\n"
            "Do not assume the next step will run.\\n"
            "Evaluation procedure (must follow all three phases):\\n"
            "1) Intent coverage: infer whether the query requires comparison, filtering by constraints, aggregation, ranking, or disambiguation.\\n"
            "2) State assessment: verify current_state has required entities, complete properties, and completed transformations.\\n"
            "3) Gap analysis: compute intent minus current_state. If any critical gap exists, output verdict=insufficient and can_answer=false.\\n"
            "Insufficient includes missing data AND missing transformations (compare/rank/aggregate), unapplied constraints, or unresolved ambiguity.\\n"
            "Adversarial examples:\\n"
            "Case 1 (false positive): Query='Compare density of aluminum and copper'; state has density_aluminum and density_copper only.\\n"
            'Expected: {"verdict":"insufficient","can_answer":false,"missing_information":["comparison not performed"],"risk_if_stop":"high"}.\\n'
            "Case 2 (truly sufficient): state has comparison_result='Copper is denser than aluminum'.\\n"
            'Expected: {"verdict":"sufficient","can_answer":true,"risk_if_stop":"low"}.\\n'
            "Return STRICT JSON only with keys: verdict, confidence, missing_information, risk_if_stop, can_answer, reasoning.\\n"
            "Schema constraints:\\n"
            "- verdict: 'sufficient' or 'insufficient'\\n"
            "- confidence: float in [0,1]\\n"
            "- missing_information: list[str]\\n"
            "- risk_if_stop: 'low'|'medium'|'high'\\n"
            "- can_answer: boolean\\n"
            "INPUT:\\n"
            f"{json.dumps(evaluator_input, ensure_ascii=True)[:6000]}"
        )

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse evaluator JSON payload robustly."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def _coerce_feedback(self, parsed: Dict[str, Any]) -> EvaluatorFeedback:
        verdict_raw = str(parsed.get("verdict", "")).strip().lower()
        if verdict_raw not in {"sufficient", "insufficient"}:
            verdict_raw = (
                "sufficient"
                if bool(parsed.get("sufficient", False))
                else "insufficient"
            )

        confidence = self._clamp_confidence(parsed.get("confidence", 0.0))
        missing_information = self._normalize_missing_information(
            parsed.get("missing_information", [])
        )

        risk_raw = str(parsed.get("risk_if_stop", "")).strip().lower()
        if risk_raw not in {"low", "medium", "high"}:
            risk_raw = self._derive_risk(verdict_raw, confidence, missing_information)

        if isinstance(parsed.get("can_answer"), bool):
            can_answer = bool(parsed.get("can_answer"))
        else:
            can_answer = (
                verdict_raw == "sufficient"
                and confidence >= 0.75
                and risk_raw != "high"
            )

        reasoning = str(parsed.get("reasoning", "")).strip() or "evaluation_complete"
        return EvaluatorFeedback(
            verdict=verdict_raw,
            confidence=confidence,
            missing_information=missing_information,
            risk_if_stop=risk_raw,
            can_answer=can_answer,
            reasoning=reasoning,
        )

    def _clamp_confidence(self, value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, parsed))

    def _normalize_missing_information(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        out: List[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                out.append(text)
        return out

    def _derive_risk(
        self, verdict: str, confidence: float, missing_information: List[str]
    ) -> str:
        if verdict != "sufficient":
            return "high"
        if missing_information:
            return "medium"
        if confidence >= 0.85:
            return "low"
        return "medium"
