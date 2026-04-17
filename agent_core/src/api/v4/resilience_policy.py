from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResilienceDecision:
    level: int
    action: str
    reason: str
    details: dict[str, Any]


class ResiliencePolicy:
    """Deterministic and reproducible resilience fallback policy."""

    def __init__(self) -> None:
        self._db_tool = "query_materials_database"
        self._rag_tool = "document_rag"

    def classify_query_type(self, query: str) -> str:
        normalized = str(query or "").strip().lower()
        property_terms = (
            "band gap",
            "bandgap",
            "density",
            "formation energy",
            "energy above hull",
            "property",
        )
        literature_terms = (
            "paper",
            "papers",
            "literature",
            "doi",
            "study",
            "publication",
            "article",
            "document",
        )

        if any(term in normalized for term in literature_terms):
            return "literature"
        if any(term in normalized for term in property_terms):
            return "property_query"
        return "property_query"

    def level2_for_planner_failure(self, query: str, reason: str) -> ResilienceDecision:
        query_type = self.classify_query_type(query)
        selected_tool = self._db_tool if query_type == "property_query" else self._rag_tool
        return ResilienceDecision(
            level=2,
            action="force_single_tool_plan",
            reason=reason,
            details={
                "query_type": query_type,
                "selected_tool": selected_tool,
                "deterministic": True,
            },
        )

    def level3_for_tool_failures(
        self,
        *,
        failed_tools: int,
        invalid_or_empty_results: int,
    ) -> ResilienceDecision | None:
        if failed_tools < 2 and invalid_or_empty_results < 2:
            return None
        return ResilienceDecision(
            level=3,
            action="final_model_direct_fallback",
            reason="multiple_tool_failures_or_invalid_results",
            details={
                "failed_tools": failed_tools,
                "invalid_or_empty_results": invalid_or_empty_results,
                "model": "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
                "fallback_mode": "direct_final_model",
                "deterministic": True,
            },
        )

    def level4_for_final_model_failure(self, error: str) -> ResilienceDecision:
        return ResilienceDecision(
            level=4,
            action="explicit_limitation_response",
            reason="final_model_failed",
            details={
                "error": str(error),
                "deterministic": True,
            },
        )
