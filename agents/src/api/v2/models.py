import json
import logging
import os
from typing import Any, Dict

import ollama

from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
)

logger = logging.getLogger(__name__)


def _extract_json_dict(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError("Model output does not contain a JSON object")

    candidate = text[first : last + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON must be an object")
    return parsed


class DecisionModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def call(self, payload: DecisionModelInput) -> DecisionModelOutput:
        prompt = self._build_prompt(payload)
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.3},
        )
        raw = response.get("message", {}).get("content", "")
        data = _extract_json_dict(raw)
        return DecisionModelOutput.model_validate(data)

    def _build_prompt(self, payload: DecisionModelInput) -> str:
        return f"""
You are the decision model for a materials-agent loop.

Task:
- Select exactly one action.
- If action is CALL_TOOL or RETRY_TOOL, provide tool_name and tool_arguments.
- If action is not a tool action, set tool_name to null and tool_arguments to {{}}.

Allowed actions:
- CALL_TOOL
- RETRY_TOOL
- REFINE_QUERY
- RECLASSIFY_INTENT
- THINK
- DELEGATE_TO_REASONER
- FINALIZE_SUCCESS
- FINALIZE_FAILURE

Tool schema (filtered list; use only these):
{json.dumps(payload.tools_available, ensure_ascii=True)}

Correct examples:
1) Query asks for material search and no material id is known.
{{"action":"CALL_TOOL","tool_name":"search_materials","tool_arguments":{{"query":{{"material":"Bi","filters":{{}}}}}},"confidence":0.85,"reasoning":"Need candidate material ids first."}}

2) Material id exists and properties are requested.
{{"action":"CALL_TOOL","tool_name":"get_material_properties","tool_arguments":{{"query":{{"material":"mp-23152"}},"propertys":["band_gap","is_metal"]}},"confidence":0.89,"reasoning":"Now fetch requested properties."}}

Negative examples (do NOT do):
- Do not call get_material_properties without a material id or clear material.
- Do not invent tool names not listed in tool schema.
- Do not invent argument fields outside schema.

When NOT to call tools:
- If enough evidence is already present, use DELEGATE_TO_REASONER or FINALIZE_SUCCESS.
- If query is irrecoverably malformed, use FINALIZE_FAILURE.

Current input:
query={json.dumps(payload.query, ensure_ascii=True)}
intent={json.dumps(payload.intent, ensure_ascii=True)}
state_summary={json.dumps(payload.state_summary, ensure_ascii=True)}
history={json.dumps(payload.history, ensure_ascii=True)}
current_attempt={payload.current_attempt}

Output JSON schema:
{{
  "action": "...",
  "tool_name": "... or null",
  "tool_arguments": {{...}},
  "confidence": 0.0,
  "reasoning": "..."
}}
""".strip()


class EvaluatorModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def call(self, payload: EvaluatorModelInput) -> EvaluatorModelOutput:
        prompt = self._build_prompt(payload)
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.2},
        )
        raw = response.get("message", {}).get("content", "")
        data = _extract_json_dict(raw)
        return EvaluatorModelOutput.model_validate(data)

    def _build_prompt(self, payload: EvaluatorModelInput) -> str:
        return f"""
You are the evaluator model for a materials-agent loop.

Evaluation rubric:
- sufficient: response is complete, relevant to original query, and coherent.
- insufficient: partial result, missing key fields, or not enough evidence yet.
- recoverable_error: temporary/repairable issue (retry or alternate tool could help).
- terminal_error: unrecoverable issue (cannot continue meaningfully).

You must evaluate:
- completeness
- relevance to query
- coherence of tool output

Input:
query={json.dumps(payload.query, ensure_ascii=True)}
query_intent={json.dumps(payload.query_intent, ensure_ascii=True)}
tool_name={json.dumps(payload.tool_name, ensure_ascii=True)}
expected_properties={json.dumps(payload.expected_properties or [], ensure_ascii=True)}
last_tool_result={json.dumps(payload.tool_result, ensure_ascii=True)}
accumulated_context={json.dumps(payload.accumulated_context, ensure_ascii=True)}

Output JSON schema:
{{
  "evaluation": "sufficient|insufficient|recoverable_error|terminal_error",
  "confidence": 0.0,
  "reasoning": "...",
  "missing_properties": []
}}
""".strip()


def build_models() -> tuple[DecisionModel, EvaluatorModel]:
    model_name = os.getenv("AGENTS_DECISION_MODEL", "yasserrmd/Qwen2.5-7B-Instruct-1M")
    logger.info("[agents-v2] using model=%s", model_name)
    return DecisionModel(model_name=model_name), EvaluatorModel(model_name=model_name)
