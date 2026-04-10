from __future__ import annotations

from typing import Any


class PlanStepModel:
    def __init__(self, step_id: int, tool_name: str, input: dict[str, Any]):
        self.step_id = step_id
        self.tool_name = tool_name
        self.input = input

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "input": self.input,
        }
