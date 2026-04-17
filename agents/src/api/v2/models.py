import json
import re
from typing import Any, Dict, List

from services.ollama_client import OllamaClient

from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    DomainCriticRequest,
    DomainCriticResponse,
    PlanningEvaluatorOutput,
    PlanningEvaluatorRequest,
    PlanningStep,
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


class PlanningEvaluatorModel:
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        if payload.mode == "plan":
            return self._plan(payload)
        return self._evaluate(payload)

    def _plan(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        prompt = self._build_planner_prompt(payload)
        response = self.ollama_client.chat(
            model=payload.model_name or self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return only strict JSON. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1},
        )
        raw = response.get("message", {}).get("content", "")
        data = _extract_json_dict(raw)
        steps = self._normalize_steps(data, payload)
        return PlanningEvaluatorOutput(
            steps=steps,
            stop=None,
            constraints_ok=None,
            modify_plan=None,
            feedback="",
        )

    def _evaluate(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        prompt = self._build_evaluator_prompt(payload)
        response = self.ollama_client.chat(
            model=payload.model_name or self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return only strict JSON. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1},
        )
        raw = response.get("message", {}).get("content", "")
        data = _extract_json_dict(raw)
        feedback = str(data.get("feedback", "")).strip()
        constraints_ok = bool(data.get("constraints_ok", data.get("stop", False)))
        return PlanningEvaluatorOutput(
            steps=[],
            stop=bool(data.get("stop", False)),
            constraints_ok=constraints_ok,
            modify_plan=bool(data.get("modify_plan", False)),
            feedback=feedback or "continue_with_current_plan",
        )

    def _build_planner_prompt(self, payload: PlanningEvaluatorRequest) -> str:
        candidate_tools: List[Dict[str, Any]] = []
        for item in payload.tools_available:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            candidate_tools.append(
                {
                    "name": name,
                    "description": str(item.get("description", "")).strip(),
                }
            )

        planner_input = {
            "query": payload.query,
            "state": payload.state,
            "tools_available": candidate_tools,
            "max_steps": payload.max_steps,
        }

        return (
            "You are the planner module in a materials-agent pipeline.\n"
            "Your job is only to create a tool-use plan.\n"
            "Do not evaluate completion. Do not execute tools.\n"
            "Use only tools listed in tools_available.\n"
            "Output strict JSON with schema:\n"
            '{"steps":[{"action":"use_tool","tool":"...","input":{},"purpose":"..."},'
            '{"action":"respond","purpose":"..."}]}\n'
            "Rules:\n"
            "1) action is one of use_tool or respond.\n"
            "2) use_tool must include a valid tool from tools_available.\n"
            "3) steps length must be <= max_steps.\n"
            "4) Include respond as the final action when possible.\n"
            "INPUT:\n"
            f"{json.dumps(planner_input, ensure_ascii=True)[:12000]}"
        )

    def _build_evaluator_prompt(self, payload: PlanningEvaluatorRequest) -> str:
        return f"""
You are the evaluator module in a materials-agent pipeline.

You ONLY evaluate execution status.
You do not execute tools.
You do not produce a plan.
You do not write conversation messages.

Decide whether execution should stop or whether the plan must be regenerated.
Return strict JSON only with keys: stop, constraints_ok, modify_plan, feedback.

Input:
query={json.dumps(payload.query, ensure_ascii=True)}
history={json.dumps(payload.history, ensure_ascii=True)}
plan={json.dumps(payload.plan, ensure_ascii=True)}
state={json.dumps(payload.state, ensure_ascii=True)}
execution_state={json.dumps(payload.execution_state, ensure_ascii=True)}

Output JSON schema:
{{
  "stop": true,
    "constraints_ok": true,
  "modify_plan": false,
  "feedback": "short internal control feedback"
}}
""".strip()

    def _normalize_steps(
        self,
        parsed: Dict[str, Any],
        payload: PlanningEvaluatorRequest,
    ) -> List[PlanningStep]:
        raw_steps = parsed.get("steps")
        allowed = sorted(
            {
                str(item.get("name", "")).strip()
                for item in payload.tools_available
                if isinstance(item, dict)
            }
        )

        normalized: List[PlanningStep] = []
        if isinstance(raw_steps, list):
            for raw_step in raw_steps[: payload.max_steps]:
                if not isinstance(raw_step, dict):
                    continue

                action_raw = str(raw_step.get("action", "")).strip().lower()
                action = action_raw if action_raw in {"use_tool", "respond"} else ""

                tool = str(raw_step.get("tool", "")).strip()
                if not action:
                    action = "use_tool" if tool else "respond"

                if action == "respond":
                    normalized.append(
                        PlanningStep(
                            action="respond",
                            purpose=str(raw_step.get("purpose", "")).strip()
                            or "Respond with available evidence",
                        )
                    )
                    continue

                if allowed and tool not in allowed:
                    continue

                tool_input = raw_step.get("input", raw_step.get("tool_arguments", {}))
                if not isinstance(tool_input, dict):
                    tool_input = {}

                normalized.append(
                    PlanningStep(
                        action="use_tool",
                        tool=tool,
                        input=tool_input,
                        purpose=str(
                            raw_step.get("purpose", raw_step.get("reason", ""))
                        ).strip()
                        or f"Use {tool}",
                    )
                )

        if not normalized:
            if allowed:
                normalized.append(
                    PlanningStep(
                        action="use_tool",
                        tool=allowed[0],
                        input={},
                        purpose="Collect initial evidence",
                    )
                )
            normalized.append(
                PlanningStep(
                    action="respond", purpose="Respond with available evidence"
                )
            )

        if normalized[-1].action != "respond" and len(normalized) < payload.max_steps:
            normalized.append(
                PlanningStep(
                    action="respond", purpose="Respond with available evidence"
                )
            )

        return normalized[: payload.max_steps]


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


class DomainCriticModel:
    def __init__(self, model_name: str, ollama_client: OllamaClient):
        self.model_name = model_name
        self.ollama_client = ollama_client

    def call(self, payload: DomainCriticRequest) -> DomainCriticResponse:
        prompt = self._build_prompt(payload)
        response = self.ollama_client.chat(
            model=payload.model_name or self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Return concise plain text strictly in requested format.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.0},
        )
        raw = str(response.get("message", {}).get("content", "")).strip()
        if not raw:
            raw = "VALID: no\nCONFIDENCE: 0.0\nISSUES:\n- empty_domain_critic_response"
        return DomainCriticResponse(response=raw)

    def _build_prompt(self, payload: DomainCriticRequest) -> str:
        return (
            f"{payload.prompt}\n\n"
            "INPUT:\n"
            f"user_query={json.dumps(payload.user_query, ensure_ascii=True)}\n"
            f"tool_results={json.dumps(payload.tool_results, ensure_ascii=True)}\n"
            f"reasoning_steps={json.dumps(payload.reasoning_steps, ensure_ascii=True)}\n"
            f"draft_response={json.dumps(payload.draft_response, ensure_ascii=True)}\n"
        )
