from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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


class EvaluatorModelInput(BaseModel):
    query: str
    tool_name: str
    tool_result: Dict[str, Any]
    expected_properties: Optional[List[str]] = None
    query_intent: str
    accumulated_context: List[Dict[str, Any]] = Field(default_factory=list)


class EvaluatorModelOutput(BaseModel):
    evaluation: Literal[
        "sufficient", "insufficient", "recoverable_error", "terminal_error"
    ]
    confidence: float = 0.0
    reasoning: str = ""
    missing_properties: List[str] = Field(default_factory=list)


class PlanningStep(BaseModel):
    tool: str
    reason: str


class PlannerCandidateTool(BaseModel):
    name: str
    score: float
    description: str = ""


class PlannerRequest(BaseModel):
    query: str
    state: Dict[str, Any] = Field(default_factory=dict)
    candidate_tools: List[PlannerCandidateTool] = Field(default_factory=list)
    max_steps: int = Field(default=3, ge=1, le=3)


class PlannerResponse(BaseModel):
    steps: List[PlanningStep] = Field(default_factory=list, max_items=3)
