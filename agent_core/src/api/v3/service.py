from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator
import asyncio
import hashlib
import json
import os
import time

import requests

from api.v4.service import PlannedRuntimeV4
from api.v4.state import BudgetState as BudgetStateV4
from .context_builder import ContextBuilder
from .evaluator import Evaluator
from .loop import run_loop
from .model_io import clean_model_response, extract_model_text, messages_to_history
from .policy import LegacyPolicyEngine
from .scheme import CompletionRequestV3, CompletionResponseV3
from .state import AgentState, BudgetState
from tools.config import TOOL_REGISTRY


FINAL_SYSTEM_PROMPT = (
    "You are a scientific assistant specialized in materials science. "
    "Answer the user query using only the provided context and clearly state uncertainty when evidence is partial."
)


class CompletionServiceV3:
    """Orchestrates deterministic loop and single final model generation."""

    def __init__(self):
        self.policy_mode = os.getenv("AGENT_POLICY_MODE", "legacy").strip().lower()
        self.legacy_policy = LegacyPolicyEngine()
        self.evaluator = Evaluator()
        self.context_builder = ContextBuilder()
        self.chat_api = (
            os.getenv("AGENTS_URL", "http://agents:8003") + "/v2/completions"
        )

        trace_dir = os.getenv("AGENT_TRACE_DIR", "agent_core/data/traces")
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.planned_runtime = PlannedRuntimeV4(trace_dir=self.trace_dir)

    def chat(self, request: CompletionRequestV3) -> CompletionResponseV3:
        if self.policy_mode == "planned":
            return self._chat_planned(request)
        return self._chat_legacy(request, report_mode="legacy")

    def stream_chat_events(self, request: CompletionRequestV3) -> Iterator[str]:
        if self.policy_mode == "planned":
            yield from self._stream_planned(request)
            return
        yield from self._stream_legacy(request, report_mode="legacy")

    def _build_initial_state(
        self,
        request: CompletionRequestV3,
        *,
        request_id: str | None = None,
    ) -> AgentState:
        return AgentState(
            request_id=request_id or self._generate_request_id(request.query),
            query=request.query,
            intent=self.legacy_policy.classify_intent(request.query),
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_context_tokens=request.max_context_tokens,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
        )

    def _chat_legacy(
        self,
        request: CompletionRequestV3,
        *,
        report_mode: str,
        request_id: str | None = None,
        fallback_reason: str | None = None,
    ) -> CompletionResponseV3:
        state = self._build_initial_state(request, request_id=request_id)
        state = run_loop(state, self.legacy_policy, self.evaluator, TOOL_REGISTRY)

        context = self.context_builder.build(state)
        state.final_answer = self._final_model_call(
            query=state.query,
            context=context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )

        self._persist_trace(state)
        response = self._build_response(state)
        self._set_mode_metadata(response, report_mode, fallback_reason)
        return response

    def _stream_legacy(
        self,
        request: CompletionRequestV3,
        *,
        report_mode: str,
        request_id: str | None = None,
        fallback_reason: str | None = None,
    ) -> Iterator[str]:
        state = self._build_initial_state(request, request_id=request_id)
        yield self._format_sse(
            "start", {"request_id": state.request_id, "query": state.query}
        )

        state = run_loop(state, self.legacy_policy, self.evaluator, TOOL_REGISTRY)
        yield self._format_sse(
            "loop_done",
            {
                "request_id": state.request_id,
                "stop_reason": state.stop_reason,
                "iterations": state.budget.iterations_used,
                "tool_calls": state.budget.tool_calls_used,
            },
        )

        context = self.context_builder.build(state)
        state.final_answer = self._final_model_call(
            query=state.query,
            context=context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )

        self._persist_trace(state)
        response = self._build_response(state)
        self._set_mode_metadata(response, report_mode, fallback_reason)
        yield self._format_sse(
            "final", {"request_id": state.request_id, "response": response.model_dump()}
        )

    def _chat_planned(self, request: CompletionRequestV3) -> CompletionResponseV3:
        request_id = self._generate_request_id(request.query)
        state, emitter, planner_outcome = self.planned_runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetStateV4(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            registry=TOOL_REGISTRY,
            stream=False,
        )

        if planner_outcome.plan is None:
            return self._chat_legacy(
                request,
                report_mode="planned",
                request_id=request_id,
                fallback_reason=planner_outcome.fallback_reason,
            )

        context = self.planned_runtime.build_context(state)
        state.final_answer = self._final_model_call_v4(
            query=state.query,
            context=context,
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
        return self._build_response_planned(state, context)

    def _stream_planned(self, request: CompletionRequestV3) -> Iterator[str]:
        request_id = self._generate_request_id(request.query)
        state, emitter, planner_outcome = self.planned_runtime.execute(
            request_id=request_id,
            query=request.query,
            budget=BudgetStateV4(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
            registry=TOOL_REGISTRY,
            stream=True,
        )

        if planner_outcome.plan is None:
            yield from self._stream_legacy(
                request,
                report_mode="planned",
                request_id=request_id,
                fallback_reason=planner_outcome.fallback_reason,
            )
            return

        yield self._format_sse(
            "start", {"request_id": state.request_id, "query": state.query}
        )

        context = self.planned_runtime.build_context(state)
        state.final_answer = self._final_model_call_v4(
            query=state.query,
            context=context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )
        response = self._build_response_planned(state, context)
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

    def _final_model_call(
        self, query: str, context: str, temperature: float, max_tokens: int
    ) -> str:
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": query},
        ]
        payload = {
            "history": messages_to_history(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = requests.post(
                self.chat_api,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return clean_model_response(extract_model_text(data))
        except Exception as exc:
            return f"Execution finished with stop_reason={context[:120]}. Final model call failed: {exc}"

    def _final_model_call_v4(
        self, query: str, context: str, temperature: float, max_tokens: int
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
        }
        try:
            response = requests.post(
                self.chat_api,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return clean_model_response(extract_model_text(data))
        except Exception as exc:
            return f"Planned execution finished without final model answer: {exc}"

    def _build_response(self, state: AgentState) -> CompletionResponseV3:
        context = self.context_builder.build(state)
        prompt_tokens = state.approximate_tokens(
            state.query
        ) + state.approximate_tokens(context)
        completion_tokens = state.approximate_tokens(state.final_answer)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "context_tokens": state.approximate_tokens(context),
        }
        metadata: Dict[str, Any] = {
            "policy_mode": "legacy",
            "iterations_count": state.budget.iterations_used,
            "tool_calls_count": state.budget.tool_calls_used,
            "context_tokens_used": state.budget.context_tokens_used,
            "stop_reason": state.stop_reason,
            "elapsed_ms": state.elapsed_ms(),
            "materials_found": len(state.materials_found),
            "documents_found": len(state.documents),
            "insights_found": len(state.extracted_insights),
            "confidence_trajectory": state.confidence_trajectory,
            "risk_trajectory": state.risk_trajectory,
            "evaluation_trace": state.evaluation_trace,
            "evaluator_feedback": [f.__dict__ for f in state.evaluator_feedback[-3:]],
        }
        return CompletionResponseV3(
            id=state.request_id,
            choices=[{"text": state.final_answer}],
            usage=usage,
            metadata=metadata,
        )

    def _build_response_planned(self, state, context: str) -> CompletionResponseV3:
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
        metadata: Dict[str, Any] = {
            "policy_mode": "planned",
            "iterations_count": state.budget.iterations_used,
            "tool_calls_count": state.budget.tool_calls_used,
            "stop_reason": state.stop_reason,
            "elapsed_ms": state.budget.elapsed_ms(),
            "materials_found": len(state.hypotheses),
            "documents_found": len(state.constraints.get("documents", [])),
            "plan_modifications_used": state.plan_modifications_used,
            "plan_status": state.plan.status,
            "execution_trace": [asdict(item) for item in state.execution_trace],
        }
        return CompletionResponseV3(
            id=state.request_id,
            choices=[{"text": state.final_answer or ""}],
            usage=usage,
            metadata=metadata,
        )

    def _set_mode_metadata(
        self,
        response: CompletionResponseV3,
        mode: str,
        fallback_reason: str | None,
    ) -> None:
        if response.metadata is None:
            response.metadata = {}
        response.metadata["policy_mode"] = mode
        if fallback_reason:
            response.metadata["fallback_engine"] = "legacy"
            response.metadata["fallback_reason"] = fallback_reason

    def _persist_trace(self, state: AgentState) -> None:
        payload = {
            "request_id": state.request_id,
            "query": state.query,
            "intent": state.intent,
            "stop_reason": state.stop_reason,
            "execution_status": state.execution_status,
            "budget": state.budget.__dict__,
            "tool_calls": [call.__dict__ for call in state.tool_calls],
            "policy_trace": state.policy_trace,
            "evaluator_feedback": [fb.__dict__ for fb in state.evaluator_feedback],
            "confidence_trajectory": state.confidence_trajectory,
            "risk_trajectory": state.risk_trajectory,
            "evaluation_trace": state.evaluation_trace,
            "materials_found": [m.__dict__ for m in state.materials_found],
            "documents": [d.__dict__ for d in state.documents],
            "extracted_insights": state.extracted_insights,
            "final_answer": state.final_answer,
        }
        path = self.trace_dir / f"{state.request_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)

    def _approximate_tokens(self, text: str) -> int:
        return max(1, len(text or "") // 4)

    def _format_sse(self, event: str, payload: Dict[str, Any]) -> str:
        return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=True)}\\n\\n"
