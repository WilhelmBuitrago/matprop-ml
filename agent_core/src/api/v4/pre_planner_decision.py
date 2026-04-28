from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PrePlannerDecision(BaseModel):
    """Result of pre-planner evaluation: does the query need external tools?"""

    calling_tools: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""


@dataclass(frozen=True)
class PrePlannerRoute:
    """Routing decision derived from PrePlannerDecision + tau threshold."""

    use_tools: bool
    decision: PrePlannerDecision
    route: str  # "full_pipeline" | "direct_llm"


class PrePlannerDecisionMaker:
    """Evaluates whether a query needs external tools BEFORE entry_policy.

    Uses the same DeepSeek model as the planner but with mode="pre-decision".
    If the model says calling_tools=False AND confidence >= tau, the query
    is routed directly to the final LLM (LLaMat) without entering the
    entry_policy → planner → loop pipeline.

    Decision logic:
        if calling_tools:
            → FULL AGENT PIPELINE
        else:
            if confidence >= tau:
                → DIRECT LLM (fast path)
            else:
                → FULL AGENT PIPELINE (safe path)

    On any failure (network, parse, timeout), always falls back to the
    full agent pipeline for safety.
    """

    def __init__(
        self,
        *,
        agents_url: str | None = None,
        model_name: str | None = None,
        tau: float | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._agents_url = (
            agents_url or os.getenv("AGENTS_URL", "http://agents:8003")
        ).rstrip("/")
        self._endpoint = f"{self._agents_url}/v2/planning-evaluator"
        self._model_name = model_name or os.getenv(
            "AGENT_PLANNING_EVALUATOR_MODEL",
            os.getenv("AGENT_PLANNER_MODEL", "deepseek-r1:8b"),
        )
        self._tau = tau if tau is not None else float(
            os.getenv("PRE_PLANNER_TAU", "0.75")
        )
        self._timeout_seconds = timeout_seconds

    @property
    def tau(self) -> float:
        return self._tau

    def evaluate(self, query: str) -> PrePlannerRoute:
        """Evaluate whether *query* needs external tools.

        Returns a ``PrePlannerRoute`` indicating the chosen path.
        On any failure the route defaults to the full pipeline.
        """
        logger.info(
            "pre_planner_decision_start query_len=%d tau=%.2f",
            len(query),
            self._tau,
        )

        decision = self._call_model(query)

        if decision is None:
            logger.warning("pre_planner_decision_fallback reason=model_failure")
            fallback = PrePlannerDecision(
                calling_tools=True,
                confidence=0.0,
                reasoning="Pre-planner model call failed; defaulting to full pipeline.",
            )
            return PrePlannerRoute(
                use_tools=True,
                decision=fallback,
                route="full_pipeline",
            )

        use_tools = self._apply_routing_logic(decision)
        route = "full_pipeline" if use_tools else "direct_llm"

        logger.info(
            "pre_planner_decision_end calling_tools=%s confidence=%.2f route=%s",
            decision.calling_tools,
            decision.confidence,
            route,
        )
        return PrePlannerRoute(
            use_tools=use_tools,
            decision=decision,
            route=route,
        )

    def _apply_routing_logic(self, decision: PrePlannerDecision) -> bool:
        """Apply the routing logic.

        Returns ``True`` when the full tool pipeline should be used.
        """
        if decision.calling_tools:
            return True

        # calling_tools is False — only skip tools if confidence is high enough
        if decision.confidence >= self._tau:
            return False  # direct LLM path

        # Low confidence → safe path → full pipeline
        return True

    # ------------------------------------------------------------------
    # Model interaction
    # ------------------------------------------------------------------

    def _call_model(self, query: str) -> PrePlannerDecision | None:
        """POST to DeepSeek with mode='pre-decision' and parse the response."""
        payload: dict[str, Any] = {
            "mode": "pre-decision",
            "query": query,
            "model_name": self._model_name,
        }

        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            parsed = response.json()
        except Exception:
            logger.exception(
                "pre_planner_decision_model_failed query_len=%d", len(query)
            )
            return None

        return self._parse_response(parsed)

    @staticmethod
    def _parse_response(parsed: Any) -> PrePlannerDecision | None:
        """Extract PrePlannerDecision from the model response.

        Accepts several response shapes:
          - {"calling_tools": bool, "confidence": float, "reasoning": str}
          - {"response": "{json_string}"}  (stringified JSON inside response key)
        """
        if not isinstance(parsed, dict):
            logger.warning("pre_planner_decision_parse_fail reason=not_a_dict")
            return None

        # Direct shape: top-level keys
        if "calling_tools" in parsed:
            return _safe_build(parsed)

        # Nested inside "response" as a JSON string
        raw_response = parsed.get("response")
        if isinstance(raw_response, str):
            try:
                inner = json.loads(raw_response)
                if isinstance(inner, dict) and "calling_tools" in inner:
                    return _safe_build(inner)
            except (json.JSONDecodeError, ValueError):
                pass

        # Nested inside "choices"
        choices = parsed.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                content = (
                    first.get("message", {}).get("content")
                    or first.get("text")
                )
                if isinstance(content, str):
                    try:
                        inner = json.loads(content)
                        if isinstance(inner, dict) and "calling_tools" in inner:
                            return _safe_build(inner)
                    except (json.JSONDecodeError, ValueError):
                        pass

        logger.warning("pre_planner_decision_parse_fail reason=missing_calling_tools")
        return None


def _safe_build(data: dict[str, Any]) -> PrePlannerDecision | None:
    """Build a ``PrePlannerDecision`` defensively."""
    try:
        calling_tools = bool(data.get("calling_tools", True))
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        reasoning = str(data.get("reasoning", ""))
        return PrePlannerDecision(
            calling_tools=calling_tools,
            confidence=confidence,
            reasoning=reasoning,
        )
    except (TypeError, ValueError) as exc:
        logger.warning("pre_planner_decision_build_fail error=%s", exc)
        return None
