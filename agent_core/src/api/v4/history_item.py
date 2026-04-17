from __future__ import annotations

from typing import Any


HISTORY_TYPES = [
    "query",
    "plan",
    "tool_call",
    "tool_result",
    "evaluation",
    "domain_critic",
]


class HistoryItem:
    def __init__(
        self,
        role: str,
        type: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        if type not in HISTORY_TYPES:
            raise ValueError(f"invalid_history_type: {type}")
        self.role = role
        self.type = type
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryItem":
        return cls(
            role=str(data.get("role", "assistant")),
            type=str(data.get("type", "tool_result")),
            content=data.get("content"),
            metadata=(
                data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            ),
        )
