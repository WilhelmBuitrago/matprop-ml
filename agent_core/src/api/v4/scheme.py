from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class CompletionRequestV4(BaseModel):
    """Public request contract for /v4/completions."""

    query: str = Field(min_length=1, max_length=10000)
    stream: bool = False
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens_for_response: int = Field(default=512, ge=32, le=4096)

    max_iterations: int = Field(default=8, ge=1, le=32)
    max_tool_calls: int = Field(default=8, ge=1, le=32)
    max_context_tokens: int = Field(default=2048, ge=256, le=8192)
    max_wall_time_ms: int | None = Field(default=None, ge=1000, le=120000)

    @field_validator("query")
    @classmethod
    def _normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class CompletionResponseV4(BaseModel):
    """Public response contract for /v4/completions."""

    id: str
    object: str = "text_completion"
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None
    metadata: dict[str, Any] | None = None
