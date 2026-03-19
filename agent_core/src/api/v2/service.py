from .scheme import CompletionRequestV2, CompletionResponseV2
from .state import (
    ActionType,
    AgentState,
    BudgetState,
    DecisionRecord,
    EvaluationResult,
    Observation,
)
from .policy import PolicyEngine
from .tool_layer import ToolExecutionLayer
from .context_builder import ContextBuilder
from .evaluator import Evaluator
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from tools.tools import SearchMaterialsTool, GetMaterialPropertiesTool

from typing import Any, Dict, Iterator, Optional, Tuple
from pathlib import Path
import hashlib
import json
import logging
import requests
import time

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class CompletionServiceV2:
    def __init__(self):
        self.chat_api = (
            os.getenv("BACKEND_LLM_URL", "http://backend-llm:8001") + "/v1/chat"
        )
        self.timeout_seconds = int(os.getenv("INTERNAL_HTTP_TIMEOUT_SECONDS", "20"))

        self.tools = {
            "search_materials": SearchMaterialsTool(),
            "get_material_properties": GetMaterialPropertiesTool(),
            "delegate_to_reasoner": None,
        }

        self.http = requests.Session()
        self.policy = PolicyEngine()
        self.evaluator = Evaluator()
        self.tool_layer = ToolExecutionLayer(self.tools)

        trace_dir = os.getenv("AGENT_TRACE_DIR", "agent_core/data/traces")
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def chat(self, request: CompletionRequestV2) -> CompletionResponseV2:
        state, context_builder = self._build_initial_state(request)

        for _ in self._agent_event_stream(state, context_builder, request):
            pass

        if not state.final_answer:
            fallback_context = context_builder.build(state)
            state.final_answer = self._call_reasoner(
                prompt=state.query,
                context=fallback_context,
                temperature=request.temperature,
            )

        self._persist_trace(state)
        return self._build_completion_response(state, context_builder)

    def stream_chat_events(self, request: CompletionRequestV2) -> Iterator[str]:
        state, context_builder = self._build_initial_state(request)

        yield self._format_sse(
            "status",
            {
                "text": "Iniciando analisis del contexto...",
                "action": "START",
                "request_id": state.request_id,
            },
        )

        for event in self._agent_event_stream(state, context_builder, request):
            yield self._format_sse(event["type"], event)

        if not state.final_answer:
            yield self._format_sse(
                "status",
                {
                    "type": "status",
                    "text": "Sintetizando informacion final...",
                    "action": ActionType.DELEGATE_TO_REASONER.value,
                    "request_id": state.request_id,
                },
            )
            fallback_context = context_builder.build(state)
            state.final_answer = self._call_reasoner(
                prompt=state.query,
                context=fallback_context,
                temperature=request.temperature,
            )

        self._persist_trace(state)

        response = self._build_completion_response(state, context_builder)
        yield self._format_sse(
            "final",
            {
                "type": "final",
                "text": state.final_answer,
                "metadata": response.metadata,
            },
        )
        yield self._format_sse("done", {"type": "done", "request_id": state.request_id})

    def _build_initial_state(self, request: CompletionRequestV2):
        request_id = hashlib.md5(
            f"{request.prompt}-{time.time_ns()}".encode("utf-8")
        ).hexdigest()

        initial_intent = self.policy.classify_intent(request.prompt)
        state = AgentState(
            request_id=request_id,
            query=request.prompt,
            intent_current=initial_intent,
            intent_history=[initial_intent],
            material_hint=self.policy.extract_material_hint(request.prompt),
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_context_tokens=request.max_tokens_for_context,
                max_wall_time_ms=request.max_wall_time_ms,
                max_reclassifications=request.max_reclassifications,
                max_think_steps=request.max_think_steps,
            ),
        )

        context_builder = ContextBuilder(
            max_context_tokens=request.max_tokens_for_context
        )

        return state, context_builder

    def _agent_event_stream(
        self,
        state: AgentState,
        context_builder: ContextBuilder,
        request: CompletionRequestV2,
    ) -> Iterator[Dict[str, Any]]:

        while state.execution_status == "running":
            action, reason_code, allowed_actions, tool_priority = (
                self.policy.choose_next_action(state)
            )
            state.previous_action = state.last_action
            state.last_action = action

            state.decisions.append(
                DecisionRecord(
                    iteration=state.budget.iterations_used + 1,
                    action=action,
                    reason_code=reason_code,
                    allowed_actions=[a.value for a in allowed_actions],
                    tool_priority=tool_priority,
                    state_fingerprint=state.state_fingerprint(),
                )
            )

            start_status = self._action_status_text(action, state)
            if start_status:
                yield {
                    "type": "status",
                    "text": start_status,
                    "action": action.value,
                    "request_id": state.request_id,
                }

            if action == ActionType.THINK:
                state.budget.think_steps_used += 1
                state.strategy_note = self._build_strategy_note(state)
                state.budget.iterations_used += 1
                state.budget.context_tokens_used = state.approximate_tokens(
                    context_builder.build(state)
                )
                self._check_hard_stops(state)
                continue

            if action == ActionType.REFINE_QUERY:
                self._refine_query(state)
                state.budget.iterations_used += 1
                state.budget.context_tokens_used = state.approximate_tokens(
                    context_builder.build(state)
                )
                self._check_hard_stops(state)
                continue

            if action == ActionType.RECLASSIFY_INTENT:
                self._reclassify_intent(state)
                state.budget.iterations_used += 1
                state.budget.context_tokens_used = state.approximate_tokens(
                    context_builder.build(state)
                )
                self._check_hard_stops(state)
                continue

            if action in {ActionType.CALL_TOOL, ActionType.RETRY_TOOL}:
                tool_name, tool_args = self._choose_tool_and_args(state, action)

                yield {
                    "type": "status",
                    "text": self._tool_status_text(tool_name, action),
                    "action": action.value,
                    "tool": tool_name,
                    "request_id": state.request_id,
                }

                tool_result = self.tool_layer.execute(tool_name, tool_args)

                observation = Observation(
                    tool_name=tool_name,
                    status=tool_result.status,
                    payload=tool_result.payload_normalized,
                    elapsed_ms=tool_result.elapsed_ms,
                    validation_flags=tool_result.validation_flags,
                    error_code=tool_result.error_code,
                    error_detail=tool_result.error_detail,
                    query_used=tool_args,
                )
                state.observations.append(observation)

                evaluation = self.evaluator.evaluate(observation, state.query)
                state.evaluations.append(evaluation)

                state.last_tool_name = tool_name
                state.last_tool_arguments = tool_args
                state.budget.tool_calls_used += 1
                state.budget.iterations_used += 1
                state.budget.context_tokens_used = state.approximate_tokens(
                    context_builder.build(state)
                )

                after_tool_status = self._post_tool_status_text(observation)
                if after_tool_status:
                    yield {
                        "type": "status",
                        "text": after_tool_status,
                        "action": action.value,
                        "tool": tool_name,
                        "request_id": state.request_id,
                    }

                self._check_hard_stops(state)
                continue

            if action == ActionType.DELEGATE_TO_REASONER:
                context = context_builder.build(state)
                answer = self._call_reasoner(
                    prompt=state.query,
                    context=context,
                    temperature=request.temperature,
                )
                state.final_answer = answer
                state.execution_status = "done"
                state.stop_reason = state.stop_reason or "delegated_to_reasoner"
                break

            if action == ActionType.FINALIZE_SUCCESS:
                state.execution_status = "done"
                state.stop_reason = state.stop_reason or "finalize_success"
                break

            if action == ActionType.FINALIZE_FAILURE:
                state.execution_status = "error"
                state.stop_reason = state.stop_reason or "finalize_failure"
                break

            state.execution_status = "error"
            state.stop_reason = "unknown_action"
            break

    def _action_status_text(
        self, action: ActionType, state: AgentState
    ) -> Optional[str]:
        if action == ActionType.THINK:
            return "Analizando la mejor estrategia para tu consulta..."
        if action == ActionType.REFINE_QUERY:
            return "Refinando la consulta para obtener resultados precisos..."
        if action == ActionType.RECLASSIFY_INTENT:
            return "Ajustando el tipo de busqueda segun el contexto..."
        if action == ActionType.DELEGATE_TO_REASONER:
            return "Sintetizando informacion para construir la respuesta..."
        if action == ActionType.FINALIZE_SUCCESS:
            return "Preparando respuesta final..."
        if action == ActionType.FINALIZE_FAILURE:
            return "No fue posible completar todos los pasos, preparando respuesta..."
        if action == ActionType.RETRY_TOOL and state.last_tool_name:
            return f"Reintentando herramienta {state.last_tool_name}..."
        return None

    def _tool_status_text(self, tool_name: str, action: ActionType) -> str:
        if tool_name == "search_materials":
            if action == ActionType.RETRY_TOOL:
                return "Reintentando busqueda de material en Materials Project..."
            return "Buscando material en Materials Project..."
        if tool_name == "get_material_properties":
            if action == ActionType.RETRY_TOOL:
                return "Reintentando consulta de propiedades del material..."
            return "Consultando propiedades del material..."
        return f"Ejecutando herramienta {tool_name}..."

    def _post_tool_status_text(self, observation: Observation) -> Optional[str]:
        if observation.status != "ok":
            return "La herramienta devolvio un resultado incompleto, ajustando estrategia..."

        if observation.tool_name == "search_materials":
            if isinstance(observation.payload, list) and observation.payload:
                first = observation.payload[0]
                material_id = (
                    str(first.get("material_id"))
                    if isinstance(first, dict) and first.get("material_id")
                    else "material"
                )
                return f"Material encontrado: {material_id}."
            return "Busqueda completada, sin coincidencias claras."

        if observation.tool_name == "get_material_properties":
            return "Propiedades recuperadas, integrando evidencia..."

        return None

    def _build_completion_response(
        self,
        state: AgentState,
        context_builder: ContextBuilder,
    ) -> CompletionResponseV2:
        context_tokens = state.approximate_tokens(context_builder.build(state))
        response_tokens = state.approximate_tokens(state.final_answer)
        input_tokens = state.approximate_tokens(state.query)

        usage = {
            "prompt_tokens": input_tokens + context_tokens,
            "context_tokens": context_tokens,
            "completion_tokens": response_tokens,
            "total_tokens": input_tokens + context_tokens + response_tokens,
        }

        metadata = {
            "trace_id": state.request_id,
            "iterations_count": state.budget.iterations_used,
            "tool_calls_count": state.budget.tool_calls_used,
            "reclassifications_count": state.budget.reclassifications_used,
            "think_steps_count": state.budget.think_steps_used,
            "context_tokens_used": state.budget.context_tokens_used,
            "stop_reason": state.stop_reason,
            "elapsed_ms": state.elapsed_ms(),
        }

        return CompletionResponseV2(
            id=state.request_id,
            object="text_completion",
            choices=[{"text": state.final_answer}],
            usage=usage,
            metadata=metadata,
        )

    def _format_sse(self, event_name: str, payload: Dict[str, Any]) -> str:
        return (
            f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
        )

    def _build_strategy_note(self, state: AgentState) -> str:
        last_eval = (
            state.evaluations[-1].reason_code if state.evaluations else "no_eval"
        )
        return f"Adjusting strategy after {last_eval}. intent={state.intent_current}"

    def _refine_query(self, state: AgentState):
        # Deterministic refinement: avoid broad prompts and keep material hints explicit.
        if (
            state.material_hint
            and state.material_hint.lower() not in state.query.lower()
        ):
            state.query = f"{state.query}. Focus material: {state.material_hint}"
        else:
            state.query = f"{state.query}. Return concise, verifiable material data."

    def _reclassify_intent(self, state: AgentState):
        state.budget.reclassifications_used += 1
        new_intent = self.policy.classify_intent(state.query)
        if new_intent == state.intent_current:
            # Force a structural strategy shift when classifier is stable.
            new_intent = (
                "property_lookup"
                if state.intent_current == "material_lookup"
                else "material_lookup"
            )
        state.intent_history.append(new_intent)
        state.intent_current = new_intent

    def _choose_tool_and_args(
        self, state: AgentState, action: ActionType
    ) -> Tuple[str, Dict[str, Any]]:
        if (
            action == ActionType.RETRY_TOOL
            and state.last_tool_name
            and state.last_tool_arguments
        ):
            return state.last_tool_name, state.last_tool_arguments

        priority = self.policy.tool_priority(state.intent_current)
        already_called = [obs.tool_name for obs in state.observations]

        selected = None
        for tool_name in priority:
            if tool_name not in already_called:
                selected = tool_name
                break

        if selected is None:
            selected = priority[0] if priority else "search_materials"

        if selected == "search_materials":
            material = state.material_hint or "Si"
            return selected, {"query": {"material": material, "filters": {}}}

        properties = self.policy.extract_property_list(state.query)
        query_material = (
            state.material_hint or self._latest_material_id_from_search(state) or "Si"
        )
        return selected, {
            "query": {"material": query_material},
            "propertys": properties,
        }

    def _latest_material_id_from_search(self, state: AgentState) -> Optional[str]:
        for obs in reversed(state.observations):
            if (
                obs.tool_name == "search_materials"
                and isinstance(obs.payload, list)
                and obs.payload
            ):
                first = obs.payload[0]
                if isinstance(first, dict) and first.get("material_id"):
                    return str(first["material_id"])
        return None

    def _check_hard_stops(self, state: AgentState):
        if state.elapsed_ms() >= state.budget.max_wall_time_ms:
            state.execution_status = "done"
            state.stop_reason = "max_wall_time_ms"
            return

        if state.budget.iterations_used >= state.budget.max_iterations:
            state.execution_status = "done"
            state.stop_reason = "max_iterations"
            return

        if state.budget.tool_calls_used >= state.budget.max_tool_calls:
            state.stop_reason = state.stop_reason or "max_tool_calls"

        if state.budget.context_tokens_used >= state.budget.max_context_tokens:
            state.execution_status = "done"
            state.stop_reason = "max_context_tokens"

    def _call_reasoner(self, prompt: str, context: str, temperature: float) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": prompt},
            ]
        }
        try:
            response = self.http.post(
                self.chat_api,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )
            return response.json().get("response", "")
        except Exception as e:
            logger.exception("Reasoner call failed")
            return f"Unable to complete reasoning due to backend error: {e}"

    def _persist_trace(self, state: AgentState):
        trace_payload = {
            "request_id": state.request_id,
            "query": state.query,
            "intent_current": state.intent_current,
            "intent_history": state.intent_history,
            "execution_status": state.execution_status,
            "stop_reason": state.stop_reason,
            "elapsed_ms": state.elapsed_ms(),
            "budget": {
                "max_iterations": state.budget.max_iterations,
                "max_tool_calls": state.budget.max_tool_calls,
                "max_context_tokens": state.budget.max_context_tokens,
                "max_wall_time_ms": state.budget.max_wall_time_ms,
                "max_reclassifications": state.budget.max_reclassifications,
                "max_think_steps": state.budget.max_think_steps,
                "iterations_used": state.budget.iterations_used,
                "tool_calls_used": state.budget.tool_calls_used,
                "reclassifications_used": state.budget.reclassifications_used,
                "think_steps_used": state.budget.think_steps_used,
                "context_tokens_used": state.budget.context_tokens_used,
            },
            "decisions": [
                {
                    "iteration": d.iteration,
                    "action": d.action.value,
                    "reason_code": d.reason_code,
                    "allowed_actions": d.allowed_actions,
                    "tool_priority": d.tool_priority,
                    "state_fingerprint": d.state_fingerprint,
                }
                for d in state.decisions
            ],
            "observations": [
                {
                    "tool_name": o.tool_name,
                    "status": o.status,
                    "payload": o.payload,
                    "elapsed_ms": o.elapsed_ms,
                    "validation_flags": o.validation_flags,
                    "error_code": o.error_code,
                    "error_detail": o.error_detail,
                    "query_used": o.query_used,
                }
                for o in state.observations
            ],
            "evaluations": [
                {
                    "klass": e.klass.value,
                    "reason_code": e.reason_code,
                    "details": e.details,
                }
                for e in state.evaluations
            ],
            "final_answer": state.final_answer,
        }

        out_path = self.trace_dir / f"{state.request_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(trace_payload, f, ensure_ascii=True, indent=2)
