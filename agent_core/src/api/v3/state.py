from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
import time


ExecutionStatus = Literal["running", "done", "error"]


@dataclass(frozen=True)
class MaterialRecord:
    """Normalized material information stored in state evidence."""

    material_id: str
    formula: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentRecord:
    """Normalized document information stored in state evidence."""

    title: str
    source: str
    relevance_score: float
    abstract: str = ""


@dataclass(frozen=True)
class ToolExecutionRecord:
    """Immutable record for each executed tool call."""

    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    status: Literal["success", "error"]
    error_code: Optional[str]
    elapsed_ms: int


@dataclass(frozen=True)
class EvaluatorFeedback:
    """Bounded evaluator output used as policy signal only."""

    sufficient: bool
    confidence: float
    missing_information: List[str]
    reasoning: str


@dataclass
class BudgetState:
    """Tracks hard runtime limits for deterministic loop control."""

    max_iterations: int = 8
    max_tool_calls: int = 8
    max_context_tokens: int = 2048
    max_wall_time_ms: int = 30000

    iterations_used: int = 0
    tool_calls_used: int = 0
    context_tokens_used: int = 0


@dataclass
class AgentState:
    """Single source of truth for the v3 hybrid agent."""

    request_id: str
    query: str
    intent: str
    budget: BudgetState = field(default_factory=BudgetState)

    materials_found: List[MaterialRecord] = field(default_factory=list)
    properties_collected: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    documents: List[DocumentRecord] = field(default_factory=list)
    extracted_insights: List[Dict[str, Any]] = field(default_factory=list)

    tool_calls: List[ToolExecutionRecord] = field(default_factory=list)
    evaluator_feedback: List[EvaluatorFeedback] = field(default_factory=list)
    policy_trace: List[Dict[str, Any]] = field(default_factory=list)

    execution_status: ExecutionStatus = "running"
    stop_reason: Optional[str] = None
    stall_counter: int = 0
    started_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    final_answer: str = ""

    def elapsed_ms(self) -> int:
        """Return elapsed wall time for this request."""
        return int(time.time() * 1000) - self.started_at_ms

    def approximate_tokens(self, text: str) -> int:
        """Cheap token estimate used for budget enforcement."""
        return max(1, len(text) // 4)

    def can_continue(self) -> bool:
        """Check hard limits and execution status before another iteration."""
        if self.execution_status != "running":
            return False
        if self.budget.iterations_used >= self.budget.max_iterations:
            self.stop_reason = "max_iterations"
            self.execution_status = "done"
            return False
        if self.budget.tool_calls_used >= self.budget.max_tool_calls:
            self.stop_reason = "max_tool_calls"
            self.execution_status = "done"
            return False
        if self.budget.context_tokens_used >= self.budget.max_context_tokens:
            self.stop_reason = "max_context_tokens"
            self.execution_status = "done"
            return False
        if self.elapsed_ms() >= self.budget.max_wall_time_ms:
            self.stop_reason = "max_wall_time_ms"
            self.execution_status = "done"
            return False
        return True
