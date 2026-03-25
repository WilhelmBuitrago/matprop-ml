from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CompletionRequest(BaseModel):
    history: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 512


class CifRequest(BaseModel):
    compound_name: str
    max_tokens: int = 512


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
