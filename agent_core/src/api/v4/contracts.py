from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


PlanStatus = Literal["active", "completed", "exhausted"]
RiskLevel = Literal["low", "medium", "high"]
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


class PlanChange(BaseModel):
    action: Literal["insert", "remove", "replace"]
    index: int = Field(ge=0)
    step: PlanStep | None = None

    @model_validator(mode="after")
    def _validate_change_shape(self) -> "PlanChange":
        if self.action in {"insert", "replace"} and self.step is None:
            raise ValueError(f"action='{self.action}' requires non-null step")
        if self.action == "remove" and self.step is not None:
            raise ValueError("action='remove' must not include step")
        return self


class ToolResult(BaseModel):
    status: ToolStatus
    raw_output: dict[str, Any] = Field(default_factory=dict)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class EvaluatorFeedback(BaseModel):
    stop: bool
    modify_plan: bool
    suggested_changes: list[PlanChange] = Field(default_factory=list)
    confidence: float = Field(default=0.0)
    risk: RiskLevel = "medium"
    trace: str = ""

    @model_validator(mode="after")
    def _validate_confidence(self) -> "EvaluatorFeedback":
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("confidence must be in [0.0, 1.0]")
        return self


def validate_plan_changes(
    changes: list[PlanChange] | list[dict[str, Any]],
) -> list[PlanChange]:
    validated: list[PlanChange] = []
    for item in changes:
        if isinstance(item, PlanChange):
            validated.append(item)
            continue
        validated.append(PlanChange.model_validate(item))
    return validated
