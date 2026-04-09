from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import asyncio
import json

from .state import AgentState


@dataclass
class TraceEntry:
    iteration: int
    event: str
    payload: dict[str, Any]

    trace_model: str
    trace_structured: dict[str, Any] | None = None

    confidence: float | None = None
    risk: str | None = None


class TraceEmitter:
    def __init__(
        self,
        *,
        state: AgentState,
        trace_dir: Path,
        stream_enabled: bool,
    ) -> None:
        self._state = state
        self._trace_dir = trace_dir
        self._stream_enabled = stream_enabled
        self._events: list[str] = []
        self._trace_dir.mkdir(parents=True, exist_ok=True)

    async def emit(
        self,
        event: str,
        payload: dict[str, Any],
        *,
        trace: str,
        trace_structured: dict[str, Any] | None = None,
        confidence: float | None = None,
        risk: str | None = None,
    ) -> None:
        entry = TraceEntry(
            iteration=self._state.budget.iterations_used,
            event=event,
            payload=payload,
            trace_model=trace,
            trace_structured=trace_structured,
            confidence=confidence,
            risk=risk,
        )
        self._state.execution_trace.append(entry)
        if self._stream_enabled:
            self._events.append(self._format_sse(event, payload))

        await asyncio.to_thread(self._persist)

    def sse_events(self) -> list[str]:
        return list(self._events)

    def _persist(self) -> None:
        payload = {
            "request_id": self._state.request_id,
            "query": self._state.query,
            "stop_reason": self._state.stop_reason,
            "plan": self._state.plan.model_dump(),
            "budget": asdict(self._state.budget),
            "replans_used": self._state.replans_used,
            "trace": [asdict(item) for item in self._state.execution_trace],
            "final_answer": self._state.final_answer,
        }
        path = self._trace_dir / f"{self._state.request_id}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
        )

    def _format_sse(self, event: str, payload: dict[str, Any]) -> str:
        return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=True)}\\n\\n"
