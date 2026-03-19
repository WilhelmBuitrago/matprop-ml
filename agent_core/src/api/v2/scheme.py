from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class CompletionRequestV2(BaseModel):
    prompt: str
    stream: bool = False
    temperature: float = 0.2
    max_tokens_for_response: int = 512
    max_tokens_for_context: int = 1024

    max_iterations: int = 6
    max_tool_calls: int = 6
    max_wall_time_ms: int = 20000
    max_reclassifications: int = 1
    max_think_steps: int = 1


class CompletionResponseV2(BaseModel):
    id: str
    object: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
