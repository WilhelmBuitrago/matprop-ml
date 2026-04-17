from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ToolStatus = Literal["success", "error"]
ToolSource = Literal["db", "paper", "rag", "llm", "simulation"]

_VALID_SOURCES = {"db", "paper", "rag", "llm", "simulation"}


@dataclass(frozen=True)
class ToolResult:
    """Unified tool result contract across runtime and tools layers."""

    status: ToolStatus
    payload: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_detail: str | None = None
    confidence: float = 0.0
    is_synthetic: bool = False
    trace: str | None = None
    source: ToolSource = "db"
    confidence_signals: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        confidence = float(self.confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("confidence must be in [0,1]")
        object.__setattr__(self, "confidence", confidence)

        normalized_payload = dict(self.payload or {})
        payload_source = normalized_payload.get("source")

        normalized_source = self.source
        if isinstance(payload_source, str) and payload_source in _VALID_SOURCES:
            normalized_source = payload_source
        elif self.source not in _VALID_SOURCES:
            normalized_source = "db"

        normalized_is_synthetic = bool(self.is_synthetic)
        if normalized_source == "rag":
            normalized_is_synthetic = True

        object.__setattr__(self, "payload", normalized_payload)
        object.__setattr__(self, "source", normalized_source)
        object.__setattr__(self, "is_synthetic", normalized_is_synthetic)

    @property
    def raw_output(self) -> dict[str, Any]:
        return self.payload

    @property
    def structured_output(self) -> dict[str, Any]:
        return self.payload

    @property
    def error_message(self) -> str | None:
        if self.error_detail:
            return self.error_detail
        if self.error_code:
            return self.error_code
        return None

    def model_dump(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "payload": dict(self.payload),
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "confidence": self.confidence,
            "is_synthetic": self.is_synthetic,
            "trace": self.trace,
            "source": self.source,
            "confidence_signals": dict(self.confidence_signals),
            "error_message": self.error_message,
            "raw_output": dict(self.payload),
            "structured_output": dict(self.payload),
        }
