from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class ActionType(str, Enum):
    CALL_TOOL = "CALL_TOOL"
    RETRY_TOOL = "RETRY_TOOL"
    REFINE_QUERY = "REFINE_QUERY"
    RECLASSIFY_INTENT = "RECLASSIFY_INTENT"
    THINK = "THINK"
    DELEGATE_TO_REASONER = "DELEGATE_TO_REASONER"
    FINALIZE_SUCCESS = "FINALIZE_SUCCESS"
    FINALIZE_FAILURE = "FINALIZE_FAILURE"


class EvalClass(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    RECOVERABLE_ERROR = "RECOVERABLE_ERROR"
    TERMINAL_ERROR = "TERMINAL_ERROR"


@dataclass
class BudgetState:
    max_iterations: int
    max_tool_calls: int
    max_context_tokens: int
    max_wall_time_ms: int
    max_reclassifications: int
    max_think_steps: int

    iterations_used: int = 0
    tool_calls_used: int = 0
    reclassifications_used: int = 0
    think_steps_used: int = 0
    context_tokens_used: int = 0


@dataclass
class Observation:
    tool_name: str
    status: str
    payload: Any
    elapsed_ms: int
    validation_flags: Dict[str, bool] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    query_used: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    klass: EvalClass
    reason_code: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRecord:
    iteration: int
    action: ActionType
    reason_code: str
    allowed_actions: List[str]
    tool_priority: List[str]
    state_fingerprint: str


@dataclass
class AgentState:
    request_id: str
    query: str
    intent_current: str
    intent_history: List[str]
    execution_status: str = "running"
    stop_reason: Optional[str] = None
    final_answer: str = ""

    started_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    last_action: Optional[ActionType] = None
    previous_action: Optional[ActionType] = None

    observations: List[Observation] = field(default_factory=list)
    evaluations: List[EvaluationResult] = field(default_factory=list)
    decisions: List[DecisionRecord] = field(default_factory=list)

    last_tool_name: Optional[str] = None
    last_tool_arguments: Optional[Dict[str, Any]] = None
    material_hint: Optional[str] = None
    strategy_note: str = ""

    budget: Optional[BudgetState] = None

    def elapsed_ms(self) -> int:
        return int(time.time() * 1000) - self.started_at_ms

    def approximate_tokens(self, text: str) -> int:
        return len(text) // 4

    def state_fingerprint(self) -> str:
        latest_eval = self.evaluations[-1].klass.value if self.evaluations else "NONE"
        return (
            f"intent={self.intent_current}|"
            f"iter={self.budget.iterations_used if self.budget else 0}|"
            f"tools={self.budget.tool_calls_used if self.budget else 0}|"
            f"eval={latest_eval}|"
            f"obs={len(self.observations)}"
        )
