import json
import re
from typing import Any, Dict, List

from services.ollama_client import OllamaClient

from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
    PlannerRequest,
    PlannerResponse,
)


def _extract_json_dict(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError("Model output does not contain a JSON object")

    candidate = text[first : last + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON must be an object")
    return parsed


def _safe_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    list_match = re.search(r"\[(?:.|\n)*\]", text)
    if list_match:
        try:
            return json.loads(list_match.group(0))
        except json.JSONDecodeError:
            pass

    object_match = re.search(r"\{(?:.|\n)*\}", text)
    if object_match:
        try:
            return json.loads(object_match.group(0))
        except json.JSONDecodeError:
            pass
    return []


class DecisionModel:
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(self, payload: DecisionModelInput) -> DecisionModelOutput:
        prompt = self._build_prompt(payload)
        response = self.ollama_client.chat(
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
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(self, payload: EvaluatorModelInput) -> EvaluatorModelOutput:
        prompt = self._build_prompt(payload)
        response = self.ollama_client.chat(
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


class InsightsModel:
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(
        self,
        *,
        query: str,
        title: str,
        section: str,
        page: int,
        chunk: str,
        max_items: int,
        max_tokens: int,
    ) -> List[str]:
        prompt = self._build_prompt(
            query=query,
            title=title,
            section=section,
            page=page,
            chunk=chunk,
            max_items=max_items,
        )
        response = self.ollama_client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": max_tokens},
        )
        raw = response.get("message", {}).get("content", "")
        return self._parse_output(raw)

    def _build_prompt(
        self,
        *,
        query: str,
        title: str,
        section: str,
        page: int,
        chunk: str,
        max_items: int,
    ) -> str:
        return (
            "Return strict JSON array of strings. "
            "Each item must be a concise technical fact extracted from the chunk and relevant to the query. "
            f"Use at most {max_items} facts.\n"
            f"Query: {query}\n"
            f"Title: {title}\n"
            f"Section: {section}\n"
            f"Page: {page}\n"
            f"Chunk: {chunk}"
        )

    def _parse_output(self, text: str) -> List[str]:
        parsed = _safe_json(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, dict):
            values = parsed.get("extracted_info") or parsed.get("facts") or []
            if isinstance(values, list):
                return [str(item).strip() for item in values if str(item).strip()]
        return []


class PlannerModel:
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(self, payload: PlannerRequest) -> PlannerResponse:
        prompt = self._build_prompt(payload)
        response = self.ollama_client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return strict JSON only. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.2},
        )
        raw = response.get("message", {}).get("content", "")
        parsed = _extract_json_dict(raw)
        normalized = self._normalize_steps(parsed, payload)
        return PlannerResponse.model_validate({"steps": normalized})

    def _build_prompt(self, payload: PlannerRequest) -> str:
        candidate_tools = [item.model_dump() for item in payload.candidate_tools]
        model_input = {
            "query": payload.query,
            "state": payload.state,
            "candidate_tools": candidate_tools,
            "max_steps": payload.max_steps,
        }
        return (
            "Plan the next tool actions for a deterministic materials-agent.\n"
            "Hard constraints:\n"
            "1) Use ONLY tool names from candidate_tools.\n"
            f"2) Return at most {payload.max_steps} steps.\n"
            "3) Preserve logical order: data retrieval before transformation/comparison.\n"
            '4) Return pure JSON object with schema: {"steps":[{"tool":"...","reason":"..."}]}.\n'
            "No markdown. No comments. No prose.\n"
            "INPUT:\n"
            f"{json.dumps(model_input, ensure_ascii=True)[:10000]}"
        )

    def _normalize_steps(
        self,
        parsed: Dict[str, Any],
        payload: PlannerRequest,
    ) -> List[Dict[str, str]]:
        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("Planner output missing 'steps' list")

        allowed = {item.name for item in payload.candidate_tools}
        normalized: List[Dict[str, str]] = []
        for step in raw_steps[: payload.max_steps]:
            if not isinstance(step, dict):
                continue
            tool = str(step.get("tool", "")).strip()
            reason = str(step.get("reason", "")).strip()
            if tool and tool in allowed:
                normalized.append({"tool": tool, "reason": reason})

        if not normalized:
            raise ValueError("Planner returned no valid steps")
        return normalized
