from __future__ import annotations

from typing import Any


class RuntimeState:
    def __init__(self, plan_steps: list[dict[str, Any]]):
        self.plan_cursor = 0
        self.plan_steps = plan_steps
        self.steps_status = [
            {
                "step_id": i,
                "status": "pending",
                "tool_used": None,
            }
            for i in range(len(plan_steps))
        ]

        self.materials_count = 0
        self.documents_count = 0
        self.insights_count = 0

        self.stop_reason: str | None = None

    def mark_step_done(self, idx: int, tool: str) -> None:
        if 0 <= idx < len(self.steps_status):
            self.steps_status[idx]["status"] = "done"
            self.steps_status[idx]["tool_used"] = tool

    def mark_step_failed(self, idx: int) -> None:
        if 0 <= idx < len(self.steps_status):
            self.steps_status[idx]["status"] = "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_cursor": self.plan_cursor,
            "plan_steps": self.plan_steps,
            "steps_status": self.steps_status,
            "materials_count": self.materials_count,
            "documents_count": self.documents_count,
            "insights_count": self.insights_count,
            "stop_reason": self.stop_reason,
        }
