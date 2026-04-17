from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.tool_result import ToolSource


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class ConfidenceCalculator:
    """Centralized confidence computation rules by tool source."""

    def calculate(
        self,
        *,
        source: ToolSource,
        status: str,
        payload: dict[str, Any],
        signals: dict[str, float] | None = None,
        explicit_confidence: float | None = None,
    ) -> float:
        if status != "success":
            return 0.0

        if explicit_confidence is not None:
            return _clamp(explicit_confidence)

        signal_map = dict(signals or {})

        if source in {"db", "paper"}:
            return self._deterministic(payload, signal_map)
        if source == "rag":
            return self._rag(payload, signal_map)
        if source == "llm":
            return self._llm(payload, signal_map)
        if source == "simulation":
            return self._simulation(payload, signal_map)
        return 0.0

    def _deterministic(self, payload: dict[str, Any], signals: dict[str, float]) -> float:
        completeness = self._signal(signals, payload, "completeness", default=0.92)
        consistency = self._signal(signals, payload, "consistency", default=0.95)
        score = 0.9 + 0.05 * completeness + 0.05 * consistency
        return _clamp(score, 0.9, 1.0)

    def _rag(self, payload: dict[str, Any], signals: dict[str, float]) -> float:
        avg_similarity = self._signal(signals, payload, "avg_similarity", default=0.4)
        agreement = self._signal(signals, payload, "agreement", default=0.4)
        coverage = self._signal(signals, payload, "coverage", default=0.4)
        score = 0.5 * avg_similarity + 0.3 * agreement + 0.2 * coverage
        return _clamp(score)

    def _llm(self, payload: dict[str, Any], signals: dict[str, float]) -> float:
        structure_consistency = self._signal(
            signals,
            payload,
            "structure_consistency",
            default=0.5,
        )
        low_entropy = self._signal(signals, payload, "low_entropy", default=0.5)
        score = 0.3 + 0.2 * structure_consistency + 0.1 * low_entropy
        return _clamp(score, 0.3, 0.6)

    def _simulation(self, payload: dict[str, Any], signals: dict[str, float]) -> float:
        normalized_error = self._signal(
            signals,
            payload,
            "normalized_error",
            default=1.0,
        )
        score = 1.0 - normalized_error
        return _clamp(score)

    def _signal(
        self,
        signals: dict[str, float],
        payload: dict[str, Any],
        key: str,
        *,
        default: float,
    ) -> float:
        if key in signals:
            return _clamp(signals[key])

        payload_signals = payload.get("confidence_signals")
        if isinstance(payload_signals, dict):
            value = payload_signals.get(key)
            if isinstance(value, (int, float)):
                return _clamp(float(value))

        return _clamp(default)
