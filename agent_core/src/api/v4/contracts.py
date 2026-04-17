from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from contracts.tool_result import ToolResult, ToolSource, ToolStatus


PlanStatus = Literal["active", "completed", "exhausted"]


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


class EvaluatorFeedback(BaseModel):
    stop: bool
    constraints_ok: bool = False
    modify_plan: bool
    feedback: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    domain_valid: bool = True
    domain_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    domain_issues: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    stop: bool
    modify_plan: bool
    constraints_ok: bool
    reason: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    domain_valid: bool = True
    domain_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    domain_issues: list[str] = Field(default_factory=list)

    @property
    def feedback(self) -> str:
        return self.reason
