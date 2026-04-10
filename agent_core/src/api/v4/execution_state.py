from __future__ import annotations

import time
from typing import Any


class ExecutionState:
    def __init__(
        self,
        iterations_used: int = 0,
        tool_calls_used: int = 0,
        replans_used: int = 0,
        max_iterations: int = 8,
        max_tool_calls: int = 8,
        max_wall_time_ms: int | None = None,
        started_at_ms: int | None = None,
    ):
        self.iterations_used = int(iterations_used)
        self.tool_calls_used = int(tool_calls_used)
        self.replans_used = int(replans_used)
        self.max_iterations = int(max_iterations)
        self.max_tool_calls = int(max_tool_calls)
        self.max_wall_time_ms = max_wall_time_ms
        self.started_at_ms = started_at_ms

    def ensure_started(self) -> None:
        if self.started_at_ms is None:
            self.started_at_ms = int(time.time() * 1000)

    def elapsed_ms(self) -> int:
        self.ensure_started()
        return int(time.time() * 1000) - int(self.started_at_ms or 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iterations_used": self.iterations_used,
            "tool_calls_used": self.tool_calls_used,
            "replans_used": self.replans_used,
            "max_iterations": self.max_iterations,
            "max_tool_calls": self.max_tool_calls,
            "max_wall_time_ms": self.max_wall_time_ms,
            "started_at_ms": self.started_at_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(**data)
