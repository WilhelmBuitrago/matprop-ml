from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CompletionRequestV4(BaseModel):
    """Public request contract for /v4/completions."""

    query: str
    stream: bool = False
    temperature: float = 0.2
    max_tokens_for_response: int = 512

    max_iterations: int = Field(default=8, ge=1, le=32)
    max_tool_calls: int = Field(default=8, ge=1, le=32)
    max_context_tokens: int = Field(default=2048, ge=256, le=8192)
    max_wall_time_ms: int | None = Field(default=None, ge=1000, le=120000)


class CompletionResponseV4(BaseModel):
    """Public response contract for /v4/completions."""

    id: str
    object: str = "text_completion"
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None
    metadata: dict[str, Any] | None = None
