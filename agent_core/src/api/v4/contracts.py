from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


PlanStatus = Literal["active", "completed", "exhausted"]
ToolStatus = Literal["success", "error"]


class PlanStep(BaseModel):
    tool: str = Field(min_length=1)
    target: str | None = None
    purpose: str = Field(min_length=1)


class Plan(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)
    cursor: int = Field(default=0, ge=0)
    status: PlanStatus = "active"

    @model_validator(mode="after")
    def _validate_cursor(self) -> "Plan":
        if self.steps and self.cursor > len(self.steps):
            raise ValueError("cursor cannot exceed number of steps")
        if not self.steps and self.cursor != 0:
            raise ValueError("cursor must be 0 when there are no steps")
        return self


class ToolResult(BaseModel):
    status: ToolStatus
    raw_output: dict[str, Any] = Field(default_factory=dict)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class EvaluatorFeedback(BaseModel):
    stop: bool
    constraints_ok: bool = False
    modify_plan: bool
    feedback: str = ""
