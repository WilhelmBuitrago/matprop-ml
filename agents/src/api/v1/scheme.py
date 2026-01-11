from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CompletionRequest(BaseModel):
    history: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 512


class InstructRequest(BaseModel):
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 512


class PlanStep(BaseModel):
    tool: str
    arguments: Dict[str, Any]


class IntentionRequest(BaseModel):
    model_name: str
    prompt: str
    max_tokens: int = 256


class ExecutionPlan(BaseModel):
    steps: List[PlanStep]


class PolicyOutputError(RuntimeError):
    pass
