from __future__ import annotations

from pathlib import Path
import asyncio
import json

from .loop import run_loop
from .planner import DeepSeekOneShotPlanner, PlannerOutcome
from .state import AgentState, BudgetState
from .trace import TraceEmitter
from .contracts import Plan
from .evaluator import LoopEvaluatorV4


class PlannedRuntimeV4:
    def __init__(self, *, trace_dir: Path):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
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

        planner_outcome = self.planner.build_plan(
            query=query,
            tool_catalog=registry.as_schema_catalog(),
        )
        if planner_outcome.plan is None:
            state.stop_reason = planner_outcome.fallback_reason or "planner_failed"
            return state, emitter, planner_outcome

        state.plan = planner_outcome.plan
        asyncio.run(run_loop(state, registry, self.evaluator, emitter))

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
            "plan": state.plan.model_dump(),
            "materials": material_rows,
            "constraints": state.constraints,
            "missing_properties": state.missing_properties,
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
