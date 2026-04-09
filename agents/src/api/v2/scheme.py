from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CompletionRequest(BaseModel):
    history: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 512
    model_name: str | None = None
    stop_tokens: List[str] = Field(default_factory=list)


class CifRequest(BaseModel):
    compound_name: str
    max_tokens: int = 512


class CrystalSpecExtractionRequest(BaseModel):
    query: str
    deterministic_spec: Dict[str, Any] = Field(default_factory=dict)


class CrystalCompletionRequest(BaseModel):
    system_message: str
    user_prompt: str
    temperature: float = 0.3
    max_tokens: int = 768
    stop_tokens: List[str] = Field(default_factory=list)
    model_name: str | None = None


class InsightRequest(BaseModel):
    query: str
    chunk: str
    title: str = ""
    section: str = ""
    page: int = 0
    max_tokens: int = 180


class InsightResponse(BaseModel):
    insights: List[str] = Field(default_factory=list)


class DecisionModelInput(BaseModel):
    query: str
    intent: str
    state_summary: Dict[str, Any] = Field(default_factory=dict)
    tools_available: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    current_attempt: int = 1


class DecisionModelOutput(BaseModel):
    action: str
    tool_name: Optional[str] = None
    tool_arguments: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""


class PlanningStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["use_tool", "respond"]
    tool: Optional[str] = None
    input: Dict[str, Any] = Field(default_factory=dict)
    purpose: str = ""

    @model_validator(mode="after")
    def _validate_step_shape(self) -> "PlanningStep":
        if self.action == "use_tool" and not (self.tool or "").strip():
            raise ValueError("tool is required when action='use_tool'")
        return self


class PlanningEvaluatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["plan", "evaluate"]
    query: str
    model_name: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    tools_available: List[Dict[str, Any]] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
    plan: Dict[str, Any] = Field(default_factory=dict)
    execution_state: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = Field(default=4, ge=1, le=8)


class PlanningEvaluatorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: List[PlanningStep] = Field(default_factory=list, max_items=8)
    stop: Optional[bool] = None
    constraints_ok: Optional[bool] = None
    modify_plan: Optional[bool] = None
    feedback: str = ""
