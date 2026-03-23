from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator
import hashlib
import json
import os
import time

import requests

from .context_builder import ContextBuilder
from .evaluator import Evaluator
from .loop import run_loop
from .model_io import clean_model_response, extract_model_text, messages_to_history
from .policy import PolicyEngine
from .scheme import CompletionRequestV3, CompletionResponseV3
from .state import AgentState, BudgetState
from tools.config import TOOL_REGISTRY


class CompletionServiceV3:
    """Orchestrates deterministic loop and single final model generation."""

    def __init__(self):
        self.policy = PolicyEngine()
        self.evaluator = Evaluator()
        self.context_builder = ContextBuilder()
        self.chat_api = (
            os.getenv("AGENTS_URL", "http://agents:8003") + "/v1/completions"
        )

        trace_dir = os.getenv("AGENT_TRACE_DIR", "agent_core/data/traces")
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def chat(self, request: CompletionRequestV3) -> CompletionResponseV3:
        """Run full v3 loop and return final completion response."""
        state = self._build_initial_state(request)
        state = run_loop(state, self.policy, self.evaluator, TOOL_REGISTRY)

        context = self.context_builder.build(state)
        state.final_answer = self._final_model_call(
            query=state.query,
            context=context,
            temperature=request.temperature,
            max_tokens=request.max_tokens_for_response,
        )

        self._persist_trace(state)
        return self._build_response(state)

    def stream_chat_events(self, request: CompletionRequestV3) -> Iterator[str]:
        """Emit concise SSE lifecycle events for observability."""
        state = self._build_initial_state(request)
        yield self._format_sse(
            "start", {"request_id": state.request_id, "query": state.query}
        )

        state = run_loop(state, self.policy, self.evaluator, TOOL_REGISTRY)
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
        yield self._format_sse(
            "final", {"request_id": state.request_id, "response": response.model_dump()}
        )

    def _build_initial_state(self, request: CompletionRequestV3) -> AgentState:
        request_id = hashlib.md5(
            f"{request.query}-{time.time_ns()}".encode("utf-8")
        ).hexdigest()
        return AgentState(
            request_id=request_id,
            query=request.query,
            intent=self.policy.classify_intent(request.query),
            budget=BudgetState(
                max_iterations=request.max_iterations,
                max_tool_calls=request.max_tool_calls,
                max_context_tokens=request.max_context_tokens,
                max_wall_time_ms=request.max_wall_time_ms,
            ),
        )

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
            )
            response.raise_for_status()
            data = response.json()
            return clean_model_response(extract_model_text(data))
        except Exception as exc:
            return f"Execution finished with stop_reason={context[:120]}. Final model call failed: {exc}"

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
            "iterations_count": state.budget.iterations_used,
            "tool_calls_count": state.budget.tool_calls_used,
            "context_tokens_used": state.budget.context_tokens_used,
            "stop_reason": state.stop_reason,
            "elapsed_ms": state.elapsed_ms(),
            "materials_found": len(state.materials_found),
            "documents_found": len(state.documents),
            "insights_found": len(state.extracted_insights),
            "evaluator_feedback": [f.__dict__ for f in state.evaluator_feedback[-3:]],
        }
        return CompletionResponseV3(
            id=state.request_id,
            choices=[{"text": state.final_answer}],
            usage=usage,
            metadata=metadata,
        )

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
            "materials_found": [m.__dict__ for m in state.materials_found],
            "documents": [d.__dict__ for d in state.documents],
            "extracted_insights": state.extracted_insights,
            "final_answer": state.final_answer,
        }
        path = self.trace_dir / f"{state.request_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)

    def _format_sse(self, event: str, payload: Dict[str, Any]) -> str:
        return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=True)}\\n\\n"
