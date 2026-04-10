from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
import time

from .contracts import Plan
from .constants import to_legacy_stop_reason
from .execution_state import ExecutionState
from .history_item import HistoryItem
from .runtime_state import RuntimeState

if TYPE_CHECKING:
    from .trace import TraceEntry


@dataclass
class MaterialHypothesis:
    material_id: str
    formula: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetState:
    max_iterations: int = 8
    max_tool_calls: int = 8
    max_wall_time_ms: int | None = None

    iterations_used: int = 0
    tool_calls_used: int = 0
    started_at_ms: int | None = None

    def ensure_started(self) -> None:
        if self.started_at_ms is None:
            self.started_at_ms = int(time.time() * 1000)

    def elapsed_ms(self) -> int:
        self.ensure_started()
        return int(time.time() * 1000) - int(self.started_at_ms or 0)


@dataclass
class AgentState:
    request_id: str
    query: str
    plan: Plan

    hypotheses: list[MaterialHypothesis] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    missing_properties: list[str] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    properties_collected: dict[str, Any] = field(default_factory=dict)
    extracted_insights: list[dict[str, Any]] = field(default_factory=list)

    execution_trace: list["TraceEntry"] = field(default_factory=list)
    final_answer: str | None = None

    budget: BudgetState = field(default_factory=BudgetState)
    replans_used: int = 0
    execution_state: ExecutionState | None = None
    runtime_state: RuntimeState | None = None

    history: list[HistoryItem] = field(default_factory=list)
    evaluations: list[dict[str, Any]] = field(default_factory=list)

    stop_reason: str | None = None
    stop_reason_canonical: str | None = None

    def __post_init__(self) -> None:
        if self.execution_state is None:
            self.execution_state = ExecutionState(
                iterations_used=self.budget.iterations_used,
                tool_calls_used=self.budget.tool_calls_used,
                replans_used=self.replans_used,
                max_iterations=self.budget.max_iterations,
                max_tool_calls=self.budget.max_tool_calls,
                max_wall_time_ms=self.budget.max_wall_time_ms,
                started_at_ms=self.budget.started_at_ms,
            )
        if self.runtime_state is None:
            self.runtime_state = RuntimeState(
                plan_steps=[step.model_dump() for step in self.plan.steps]
            )
        self.sync_execution_state()
        self.refresh_runtime_counts()
        if self.stop_reason_canonical and self.stop_reason is None:
            self.stop_reason = to_legacy_stop_reason(self.stop_reason_canonical)

    def sync_execution_state(self) -> None:
        if self.execution_state is None:
            return
        self.execution_state.iterations_used = self.budget.iterations_used
        self.execution_state.tool_calls_used = self.budget.tool_calls_used
        self.execution_state.replans_used = self.replans_used
        self.execution_state.max_iterations = self.budget.max_iterations
        self.execution_state.max_tool_calls = self.budget.max_tool_calls
        self.execution_state.max_wall_time_ms = self.budget.max_wall_time_ms
        self.execution_state.started_at_ms = self.budget.started_at_ms

    def refresh_runtime_counts(self) -> None:
        if self.runtime_state is None:
            return
        self.runtime_state.materials_count = len(self.hypotheses)
        self.runtime_state.documents_count = len(self.documents)
        self.runtime_state.insights_count = len(self.extracted_insights)
        self.runtime_state.plan_cursor = self.plan.cursor

    def set_stop_reason(self, canonical_reason: str) -> None:
        self.stop_reason_canonical = canonical_reason
        self.stop_reason = to_legacy_stop_reason(canonical_reason)
        if self.runtime_state is not None:
            self.runtime_state.stop_reason = canonical_reason

    @property
    def materials_found(self) -> list[MaterialHypothesis]:
        # Compatibility alias for existing tools expecting materials_found.
        return self.hypotheses
