from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import asyncio
import hashlib
import json
import os
import time
from typing import Any, Iterator

import requests

from .entry_policy import EntryPolicyV4
from .failure_policy import handle_evaluator_failure
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


class PlannedRuntimeV4:
    def __init__(self, *, trace_dir: Path):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.entry_policy = EntryPolicyV4()
        self.planner = DeepSeekOneShotPlanner()
        self.evaluator = LoopEvaluatorV4()

    def execute(
        self,
        *,
        request_id: str,
        query: str,
        budget: BudgetState,
        registry,
        stream: bool,
    ) -> tuple[AgentState, TraceEmitter, PlannerOutcome]:
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

        planner_outcome = self.planner.build_plan(
            query=query,
            tool_catalog=selected_tool_catalog,
            state={
                "entry_policy": state.constraints["entry_policy"],
            },
        )
        if planner_outcome.plan is None:
            if planner_outcome.fallback_reason == "invalid_plan":
                state.set_stop_reason("invalid_plan")
            else:
                state.set_stop_reason("planner_failed")
            return state, emitter, planner_outcome

        if planner_outcome.fallback_reason == "invalid_plan":
            state.constraints["initial_plan_fallback_reason"] = "invalid_plan"

        state.plan = planner_outcome.plan
        asyncio.run(
            run_loop(
                state,
                registry,
                self.planner,
                self.evaluator,
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
        state, emitter, planner_outcome = self.runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            registry=TOOL_REGISTRY,
            stream=False,
        )

        if planner_outcome.plan is None and not state.stop_reason:
            if planner_outcome.fallback_reason == "invalid_plan":
                state.set_stop_reason("invalid_plan")
            else:
                state.set_stop_reason("planner_failed")

        context = self.runtime.build_context(state)
        final_context = context
        if state.stop_reason_canonical == "evaluator_failed":
            mode = handle_evaluator_failure(state.history)
            if mode == "final_without_context":
                final_context = self.runtime.build_query_only_context(state)
            state.constraints["evaluator_failure_mode"] = mode

        state.final_answer = self._final_model_call_v4(
            query=state.query,
            context=final_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )
        asyncio.run(
            emitter.emit(
                "final",
                {"request_id": state.request_id},
                trace="Final answer generated",
            )
        )
        return self._build_response(
            state,
            context=final_context,
            planner_fallback_reason=planner_outcome.fallback_reason,
        )

    def stream_chat_events(self, request: CompletionRequestV4) -> Iterator[str]:
        request_id = self._generate_request_id(request.query)
        state, emitter, planner_outcome = self.runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            registry=TOOL_REGISTRY,
            stream=True,
        )

        yield self._format_sse(
            "start", {"request_id": state.request_id, "query": state.query}
        )

        if planner_outcome.plan is None and not state.stop_reason:
            if planner_outcome.fallback_reason == "invalid_plan":
                state.set_stop_reason("invalid_plan")
            else:
                state.set_stop_reason("planner_failed")

        context = self.runtime.build_context(state)
        final_context = context
        if state.stop_reason_canonical == "evaluator_failed":
            mode = handle_evaluator_failure(state.history)
            if mode == "final_without_context":
                final_context = self.runtime.build_query_only_context(state)
            state.constraints["evaluator_failure_mode"] = mode

        state.final_answer = self._final_model_call_v4(
            query=state.query,
            context=final_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )
        response = self._build_response(
            state,
            context=final_context,
            planner_fallback_reason=planner_outcome.fallback_reason,
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

    def _generate_request_id(self, query: str) -> str:
        return hashlib.md5(f"{query}-{time.time_ns()}".encode("utf-8")).hexdigest()

    def _final_model_call_v4(
        self,
        *,
        query: str,
        context: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages = [
            {"role": "system", "content": FINAL_SYSTEM_PROMPT},
            {"role": "user", "content": query},
            {"role": "assistant", "content": context},
        ]
        payload = {
            "history": messages_to_history(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model_name": self.model_name,
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
            return clean_model_response(extract_model_text(parsed))
        except Exception as exc:
            return f"Planned runtime finished without final model answer: {exc}"

    def _build_response(
        self,
        state: AgentState,
        *,
        context: str,
        planner_fallback_reason: str | None,
    ) -> CompletionResponseV4:
        prompt_tokens = self._approximate_tokens(
            state.query
        ) + self._approximate_tokens(context)
        completion_tokens = self._approximate_tokens(state.final_answer or "")
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "context_tokens": self._approximate_tokens(context),
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

    def _approximate_tokens(self, text: str) -> int:
        return max(1, len(text or "") // 4)

    def _format_sse(self, event: str, payload: dict[str, Any]) -> str:
        return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=True)}\\n\\n"
