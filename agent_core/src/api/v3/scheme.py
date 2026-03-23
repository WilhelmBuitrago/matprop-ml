from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class CompletionRequestV3(BaseModel):
    """Request contract for the deterministic v3 loop."""

    query: str
    stream: bool = False
    temperature: float = 0.2
    max_tokens_for_response: int = 512

    max_iterations: int = Field(default=8, ge=1, le=32)
    max_tool_calls: int = Field(default=8, ge=1, le=32)
    max_context_tokens: int = Field(default=2048, ge=256, le=8192)
    max_wall_time_ms: int = Field(default=30000, ge=1000, le=120000)


class CompletionResponseV3(BaseModel):
    """Response contract for v3 completions endpoint."""

    id: str
    object: str = "text_completion"
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
