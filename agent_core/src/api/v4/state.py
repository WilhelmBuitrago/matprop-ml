from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
import time

from .contracts import Plan

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
    plan_modifications_used: int = 0

    stop_reason: str | None = None

    @property
    def materials_found(self) -> list[MaterialHypothesis]:
        # Compatibility alias for existing v3-oriented tools.
        return self.hypotheses
