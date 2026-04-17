from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Iterator

import requests

from .context_budget import ContextBudget
from .entry_policy import EntryPolicyV4
from .failure_policy import handle_evaluator_failure
from .resilience_policy import ResiliencePolicy
from .loop import run_loop
from .model_io import clean_model_response, extract_model_text, messages_to_history
from .planner import DeepSeekOneShotPlanner, PlannerOutcome
from .scheme import CompletionRequestV4, CompletionResponseV4
from .state import AgentState, BudgetState
from .trace import TraceEmitter
from .contracts import Plan
from .evaluator import LoopEvaluatorV4
from tools.config import TOOL_REGISTRY


FINAL_SYSTEM_PROMPT = (
    "You are a scientific assistant specialized in materials science. "
    "Answer the user query using only the provided context and clearly state uncertainty when evidence is partial."
)

logger = logging.getLogger(__name__)

LEVEL3_FALLBACK_MODEL = "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"


class PlannedRuntimeV4:
    def __init__(self, *, trace_dir: Path):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.entry_policy = EntryPolicyV4()

    def execute(
        self,
        *,
        request_id: str,
        query: str,
        budget: BudgetState,
        max_context_tokens: int,
        registry,
        stream: bool,
    ) -> tuple[AgentState, TraceEmitter, PlannerOutcome]:
        context_budget = ContextBudget(max_tokens=max_context_tokens)
        planner = DeepSeekOneShotPlanner(context_budget=context_budget)
        evaluator = LoopEvaluatorV4(
            context_budget=context_budget,
            trace_dir=self.trace_dir,
        )

        state = AgentState(
            request_id=request_id,
            query=query,
            plan=Plan(steps=[], cursor=0, status="active"),
            budget=budget,
        )
        state.budget.ensure_started()

        emitter = TraceEmitter(
            state=state,
            trace_dir=self.trace_dir,
            stream_enabled=stream,
        )

        selected_tool_catalog = self.entry_policy.select_tools(
            query=query,
            registry=registry,
        )
        state.constraints["entry_policy"] = {
            "selected_tools": [
                str(item.get("name", "")).strip() for item in selected_tool_catalog
            ],
            "top_k": len(selected_tool_catalog),
        }
        state.constraints["context_budget"] = {
            "max_context_tokens": context_budget.max_tokens,
        }

        resilience_policy = ResiliencePolicy()

        planner_outcome = planner.build_plan(
            query=query,
            tool_catalog=selected_tool_catalog,
            state={
                "entry_policy": state.constraints["entry_policy"],
            },
        )
        if planner_outcome.plan is None:
            level2 = resilience_policy.level2_for_planner_failure(
                query,
                planner_outcome.fallback_reason or "planner_failed",
            )
            state.plan = self._build_level2_fallback_plan(
                query=query,
                selected_tool=str(
                    level2.details.get(
                        "selected_tool",
                        "query_materials_database",
                    )
                ),
            )
            state.constraints["resilience_level"] = level2.level
            state.constraints["resilience_action"] = level2.action
            state.constraints["resilience_reason"] = level2.reason
            state.constraints["resilience_details"] = dict(level2.details)
            state.constraints["initial_plan_fallback_reason"] = (
                planner_outcome.fallback_reason or "planner_failed"
            )
            planner_outcome = PlannerOutcome(
                plan=state.plan,
                fallback_reason=planner_outcome.fallback_reason,
            )
        else:
            if planner_outcome.fallback_reason == "invalid_plan":
                state.constraints["initial_plan_fallback_reason"] = "invalid_plan"

            state.plan = planner_outcome.plan

        asyncio.run(
            run_loop(
                state,
                registry,
                planner,
                evaluator,
                emitter,
                selected_tool_catalog,
            )
        )

        if state.stop_reason in {"planner_failed", "evaluator_failed"}:
            return (
                state,
                emitter,
                PlannerOutcome(plan=None, fallback_reason=state.stop_reason),
            )

        return state, emitter, planner_outcome

    def build_context(self, state: AgentState) -> str:
        material_rows = [
            {
                "material_id": item.material_id,
                "formula": item.formula,
                "properties": item.properties,
            }
            for item in state.hypotheses[:6]
        ]
        summary = {
            "query": state.query,
            "stop_reason": state.stop_reason,
            "stop_reason_canonical": state.stop_reason_canonical,
            "plan": state.plan.model_dump(),
            "execution_state": (
                state.execution_state.to_dict() if state.execution_state else {}
            ),
            "runtime_state": (
                state.runtime_state.to_dict() if state.runtime_state else {}
            ),
            "history": [item.to_dict() for item in state.history],
            "evaluations": list(state.evaluations),
            "final_answer": state.final_answer,
            "materials": material_rows,
            "constraints": state.constraints,
            "missing_properties": state.missing_properties,
            "entry_policy": state.constraints.get("entry_policy", {}),
            "trace_tail": [
                {
                    "event": entry.event,
                    "payload": entry.payload,
                    "trace_model": entry.trace_model,
                    "confidence": entry.confidence,
                    "risk": entry.risk,
                }
                for entry in state.execution_trace[-8:]
            ],
        }
        return json.dumps(summary, ensure_ascii=True)

    def build_query_only_context(self, state: AgentState) -> str:
        return json.dumps(
            {"query": state.query, "mode": "query_only"}, ensure_ascii=True
        )

    def _build_level2_fallback_plan(self, *, query: str, selected_tool: str) -> Plan:
        if selected_tool == "document_rag":
            return Plan(
                steps=[
                    {
                        "tool": "search_scientific_documents",
                        "target": query,
                        "purpose": "Collect literature candidates for deterministic RAG fallback",
                    },
                    {
                        "tool": "document_rag",
                        "target": query,
                        "purpose": "Extract evidence from retrieved papers in deterministic fallback",
                    },
                ],
                cursor=0,
                status="active",
            )

        return Plan(
            steps=[
                {
                    "tool": "query_materials_database",
                    "target": query,
                    "purpose": "Deterministic property lookup fallback",
                }
            ],
            cursor=0,
            status="active",
        )


class PlannedRuntimeV4Service:
    """Public v4 completion service.

    Planner and evaluator are separate services that share one model endpoint:
    planner runs once to produce the initial plan, while evaluator runs only
    inside the loop after each tool execution.
    """

    def __init__(self) -> None:
        self.chat_api = (
            os.getenv("AGENTS_URL", "http://agents:8003") + "/v2/completions"
        )
        self.model_name = os.getenv(
            "AGENT_PLANNING_EVALUATOR_MODEL",
            os.getenv("AGENT_BASE_MODEL", "deepseek-r1:8b"),
        )
        trace_dir = os.getenv("AGENT_TRACE_DIR", "agent_core/data/traces")
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.runtime = PlannedRuntimeV4(trace_dir=self.trace_dir)

    def chat(self, request: CompletionRequestV4) -> CompletionResponseV4:
        request_id = self._generate_request_id(request.query)
        logger.info(
            "chat_v4_start request_id=%s query_len=%d max_iterations=%d max_tool_calls=%d",
            request_id,
            len(request.query),
            request.max_iterations,
            request.max_tool_calls,
        )
        state, emitter, planner_outcome = self.runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            max_context_tokens=request.max_context_tokens,
            registry=TOOL_REGISTRY,
            stream=False,
        )

        context = self.runtime.build_context(state)
        final_context = context
        if state.stop_reason_canonical == "evaluator_failed":
            mode = handle_evaluator_failure(state.history)
            if mode == "final_without_context":
                final_context = self.runtime.build_query_only_context(state)
            state.constraints["evaluator_failure_mode"] = mode

        fallback_details = state.constraints.get("resilience_details", {})
        fallback_mode = state.constraints.get("resilience_action")
        fallback_model = None
        if fallback_mode == "final_model_direct_fallback" and isinstance(
            fallback_details, dict
        ):
            fallback_model = str(
                fallback_details.get("model") or LEVEL3_FALLBACK_MODEL
            )

        final_answer, final_error = self._final_model_call_v4(
            query=state.query,
            context=final_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
            model_name_override=fallback_model,
        )
        if final_error:
            level4 = ResiliencePolicy().level4_for_final_model_failure(final_error)
            state.constraints["resilience_level"] = level4.level
            state.constraints["resilience_action"] = level4.action
            state.constraints["resilience_reason"] = level4.reason
            state.constraints["resilience_details"] = dict(level4.details)
            final_answer = (
                "No puedo completar una respuesta confiable en este momento debido a una limitacion tecnica del modelo final. "
                "Intenta nuevamente o reformula la consulta con mas contexto experimental."
            )
        state.final_answer = final_answer

        asyncio.run(
            emitter.emit(
                "final",
                {"request_id": state.request_id},
                trace="Final answer generated",
            )
        )
        logger.info(
            "chat_v4_end request_id=%s stop_reason=%s iterations=%d tool_calls=%d",
            state.request_id,
            state.stop_reason_canonical,
            state.budget.iterations_used,
            state.budget.tool_calls_used,
        )
        return self._build_response(
            state,
            context=final_context,
            planner_fallback_reason=planner_outcome.fallback_reason,
            max_context_tokens=request.max_context_tokens,
        )

    def stream_chat_events(self, request: CompletionRequestV4) -> Iterator[str]:
        request_id = self._generate_request_id(request.query)
        logger.info(
            "chat_v4_stream_start request_id=%s query_len=%d",
            request_id,
            len(request.query),
        )
        state, emitter, planner_outcome = self.runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            max_context_tokens=request.max_context_tokens,
            registry=TOOL_REGISTRY,
            stream=True,
        )

        yield self._format_sse(
            "start", {"request_id": state.request_id, "query": state.query}
        )

        context = self.runtime.build_context(state)
        final_context = context
        if state.stop_reason_canonical == "evaluator_failed":
            mode = handle_evaluator_failure(state.history)
            if mode == "final_without_context":
                final_context = self.runtime.build_query_only_context(state)
            state.constraints["evaluator_failure_mode"] = mode

        fallback_details = state.constraints.get("resilience_details", {})
        fallback_mode = state.constraints.get("resilience_action")
        fallback_model = None
        if fallback_mode == "final_model_direct_fallback" and isinstance(
            fallback_details, dict
        ):
            fallback_model = str(
                fallback_details.get("model") or LEVEL3_FALLBACK_MODEL
            )

        final_answer, final_error = self._final_model_call_v4(
            query=state.query,
            context=final_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
            model_name_override=fallback_model,
        )
        if final_error:
            level4 = ResiliencePolicy().level4_for_final_model_failure(final_error)
            state.constraints["resilience_level"] = level4.level
            state.constraints["resilience_action"] = level4.action
            state.constraints["resilience_reason"] = level4.reason
            state.constraints["resilience_details"] = dict(level4.details)
            final_answer = (
                "No puedo completar una respuesta confiable en este momento debido a una limitacion tecnica del modelo final. "
                "Intenta nuevamente o reformula la consulta con mas contexto experimental."
            )
        state.final_answer = final_answer

        response = self._build_response(
            state,
            context=final_context,
            planner_fallback_reason=planner_outcome.fallback_reason,
            max_context_tokens=request.max_context_tokens,
        )
        asyncio.run(
            emitter.emit(
                "final",
                {"request_id": state.request_id, "response": response.model_dump()},
                trace="Final response generated",
            )
        )

        for event in emitter.sse_events():
            yield event

        logger.info(
            "chat_v4_stream_end request_id=%s stop_reason=%s iterations=%d tool_calls=%d",
            state.request_id,
            state.stop_reason_canonical,
            state.budget.iterations_used,
            state.budget.tool_calls_used,
        )

    def _generate_request_id(self, query: str) -> str:
        return hashlib.md5(f"{query}-{time.time_ns()}".encode("utf-8")).hexdigest()

    def _final_model_call_v4(
        self,
        *,
        query: str,
        context: str,
        temperature: float,
        max_tokens: int,
        model_name_override: str | None = None,
    ) -> tuple[str, str | None]:
        messages = [
            {"role": "system", "content": FINAL_SYSTEM_PROMPT},
            {"role": "user", "content": query},
            {"role": "assistant", "content": context},
        ]
        model_name = model_name_override or self.model_name
        payload = {
            "history": messages_to_history(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model_name": model_name,
        }

        try:
            response = requests.post(
                self.chat_api,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            parsed = response.json()
            return clean_model_response(extract_model_text(parsed)), None
        except Exception as exc:
            return "", str(exc)

    def _build_response(
        self,
        state: AgentState,
        *,
        context: str,
        planner_fallback_reason: str | None,
        max_context_tokens: int,
    ) -> CompletionResponseV4:
        token_budget = ContextBudget(max_tokens=max_context_tokens)
        prompt_tokens = token_budget.estimate_text_tokens(
            state.query
        ) + token_budget.estimate_text_tokens(context)
        completion_tokens = token_budget.estimate_text_tokens(state.final_answer or "")
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "context_tokens": token_budget.estimate_text_tokens(context),
        }

        metadata: dict[str, Any] = {
            "policy_mode": "planned",
            "runtime_version": "v4",
            "iterations_count": state.budget.iterations_used,
            "tool_calls_count": state.budget.tool_calls_used,
            "stop_reason": state.stop_reason,
            "stop_reason_canonical": state.stop_reason_canonical,
            "stop_reason_legacy": state.stop_reason,
            "elapsed_ms": state.budget.elapsed_ms(),
            "materials_found": len(state.hypotheses),
            "documents_found": len(state.constraints.get("documents", [])),
            "replans_used": state.replans_used,
            "plan_status": state.plan.status,
            "execution_state": (
                state.execution_state.to_dict() if state.execution_state else {}
            ),
            "runtime_state": (
                state.runtime_state.to_dict() if state.runtime_state else {}
            ),
            "evaluations": list(state.evaluations),
            "execution_trace": [asdict(item) for item in state.execution_trace],
        }
        if planner_fallback_reason:
            metadata["planner_status"] = "failed"
            metadata["planner_fallback_reason"] = planner_fallback_reason
        else:
            metadata["planner_status"] = "ok"

        return CompletionResponseV4(
            id=state.request_id,
            choices=[{"text": state.final_answer or ""}],
            usage=usage,
            metadata=metadata,
        )

    def _format_sse(self, event: str, payload: dict[str, Any]) -> str:
        return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=True)}\\n\\n"
