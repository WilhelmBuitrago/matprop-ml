from pydantic import BaseModel
from typing import List, Dict


class CompletionRequest(BaseModel):
    history: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 512


class InstructRequest(BaseModel):
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 512
