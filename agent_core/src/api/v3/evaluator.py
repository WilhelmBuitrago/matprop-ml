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
    ) -> EvaluatorFeedback:
        """Evaluate evidence quality without controlling loop behavior."""
        prompt = self._build_prompt(state, tool_name, tool_output)
        fallback = EvaluatorFeedback(
            sufficient=False,
            confidence=0.4,
            missing_information=["additional_evidence"],
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
                f"{self.model_url}/v1/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            text = clean_model_response(extract_model_text(response.json()))
            parsed = self._parse_json(text)
            return EvaluatorFeedback(
                sufficient=bool(parsed.get("sufficient", False)),
                confidence=float(parsed.get("confidence", 0.0)),
                missing_information=list(parsed.get("missing_information", [])),
                reasoning=str(parsed.get("reasoning", "")),
            )
        except Exception:
            return fallback

    def _build_prompt(
        self, state: AgentState, tool_name: str, tool_output: Dict[str, Any]
    ) -> str:
        """Construct strict JSON-only evaluator prompt."""
        latest_materials = [m.material_id for m in state.materials_found[:5]]
        latest_docs = [d.title for d in state.documents[:5]]
        return (
            "You are an evaluator, not a planner.\\n"
            "Return STRICT JSON with keys: sufficient(bool), confidence(float), missing_information(list[str]), reasoning(str).\\n"
            f"User query: {state.query}\\n"
            f"Tool name: {tool_name}\\n"
            f"Tool output: {json.dumps(tool_output, ensure_ascii=True)[:2500]}\\n"
            f"Known materials: {json.dumps(latest_materials, ensure_ascii=True)}\\n"
            f"Known documents: {json.dumps(latest_docs, ensure_ascii=True)}\\n"
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
