# agent_core/tools/api/v1/scheme.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class Tools(BaseModel):
    tools: List[Dict[str, Any]]


class CompletionRequest(BaseModel):
    prompt: str
    temperature: float = 0.7
    max_tokens_for_response: int = 512
    max_tokens_for_context: int = 1024


class CompletionResponse(BaseModel):
    id: str
    object: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
