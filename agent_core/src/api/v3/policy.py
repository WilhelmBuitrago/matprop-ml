from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re

from .state import AgentState
from tools.base import ToolRegistry


@dataclass(frozen=True)
class PolicyDecision:
    """Deterministic policy decision for one iteration."""

    tool_name: str
    tool_arguments: Dict[str, Any]
    scores: Dict[str, float]
    reasoning: str


class NoValidToolError(RuntimeError):
    """Raised when no tool passes preconditions for current state."""


class PolicyEngine:
    """Local deterministic policy with evaluator-guided scoring."""

    WEIGHTS = {
        "missing_coverage": 0.45,
        "information_gain": 0.30,
        "compatibility": 0.20,
        "cost": 0.15,
    }

    TOOL_COST = {
        "query_materials_database": 0.35,
        "compare_materials": 0.20,
        "validate_material_constraints": 0.25,
        "search_scientific_documents": 0.55,
        "document_rag": 0.80,
        "generate_crystal_structure": 0.40,
    }

    def classify_intent(self, query: str) -> str:
        """Classify request intent with deterministic keyword heuristics."""
        q = query.lower()
        if any(k in q for k in ["compare", "versus", "vs"]):
            return "compare"
        if any(k in q for k in ["constraint", "must", "at least", "less than"]):
            return "constraint_validation"
        if any(k in q for k in ["paper", "document", "literature"]):
            return "document_research"
        if any(k in q for k in ["structure", "cif", "poscar", "crystal"]):
            return "structure_generation"
        return "material_lookup"

    def decide(self, state: AgentState, registry: ToolRegistry) -> PolicyDecision:
        """Select argmax tool after precondition filtering and deterministic scoring."""
        intent = self.classify_intent(state.query)
        candidates = self._intent_candidates(intent)
        available = [name for name in candidates if registry.can_run(name, state)]
        if not available:
            raise NoValidToolError(f"No valid tools for intent={intent}")

        scores: Dict[str, float] = {}
        for tool_name in available:
            scores[tool_name] = self._score_tool(state, tool_name)

        selected = max(scores, key=scores.get)
        arguments = self._build_arguments(state, selected)
        reasoning = (
            f"intent={intent}; selected={selected}; score={scores[selected]:.3f}"
        )
        return PolicyDecision(
            tool_name=selected,
            tool_arguments=arguments,
            scores=scores,
            reasoning=reasoning,
        )

    def _intent_candidates(self, intent: str) -> List[str]:
        mapping = {
            "material_lookup": [
                "query_materials_database",
                "search_scientific_documents",
                "generate_crystal_structure",
            ],
            "compare": [
                "compare_materials",
                "query_materials_database",
            ],
            "constraint_validation": [
                "validate_material_constraints",
                "query_materials_database",
            ],
            "document_research": [
                "search_scientific_documents",
                "document_rag",
            ],
            "structure_generation": [
                "generate_crystal_structure",
                "query_materials_database",
            ],
        }
        return mapping.get(intent, ["query_materials_database"])

    def _score_tool(self, state: AgentState, tool_name: str) -> float:
        missing_coverage = self._coverage_of_missing_info(state, tool_name)
        information_gain = self._expected_information_gain(state, tool_name)
        compatibility = self._state_compatibility(state, tool_name)
        cost = self.TOOL_COST.get(tool_name, 0.5)

        w = self.WEIGHTS
        return (
            w["missing_coverage"] * missing_coverage
            + w["information_gain"] * information_gain
            + w["compatibility"] * compatibility
            - w["cost"] * cost
        )

    def _coverage_of_missing_info(self, state: AgentState, tool_name: str) -> float:
        feedback = state.evaluator_feedback[-1] if state.evaluator_feedback else None
        if not feedback or not feedback.missing_information:
            return 0.5
        miss = " ".join(feedback.missing_information).lower()
        if "document" in miss and tool_name in {
            "search_scientific_documents",
            "document_rag",
        }:
            return 1.0
        if "structure" in miss and tool_name == "generate_crystal_structure":
            return 1.0
        if "constraint" in miss and tool_name == "validate_material_constraints":
            return 1.0
        if "material" in miss and tool_name == "query_materials_database":
            return 1.0
        return 0.25

    def _expected_information_gain(self, state: AgentState, tool_name: str) -> float:
        if tool_name == "query_materials_database":
            return 0.9 if not state.materials_found else 0.2
        if tool_name == "compare_materials":
            return 0.8 if len(state.materials_found) >= 2 else 0.1
        if tool_name == "validate_material_constraints":
            return 0.7 if state.constraints else 0.2
        if tool_name == "search_scientific_documents":
            return 0.8 if not state.documents else 0.3
        if tool_name == "document_rag":
            return 0.75 if state.documents else 0.1
        if tool_name == "generate_crystal_structure":
            return 0.75
        return 0.2

    def _state_compatibility(self, state: AgentState, tool_name: str) -> float:
        if tool_name == "compare_materials" and len(state.materials_found) >= 2:
            return 1.0
        if tool_name == "validate_material_constraints" and state.constraints:
            return 1.0
        if tool_name == "document_rag" and state.documents:
            return 1.0
        if tool_name == "generate_crystal_structure":
            return 1.0
        if tool_name in {"query_materials_database", "search_scientific_documents"}:
            return 0.8
        return 0.2

    def _build_arguments(self, state: AgentState, tool_name: str) -> Dict[str, Any]:
        if tool_name == "query_materials_database":
            query_mode = self._extract_material_query(state.query)
            return {**query_mode, "filters": {}, "limit": 5}
        if tool_name == "compare_materials":
            material_ids = [m.material_id for m in state.materials_found[:5]]
            return {
                "material_ids": material_ids,
                "properties_to_compare": ["band_gap", "density", "is_stable"],
            }
        if tool_name == "validate_material_constraints":
            return {"constraints": state.constraints}
        if tool_name == "search_scientific_documents":
            hint = state.materials_found[0].formula if state.materials_found else None
            return {"query": state.query, "material_focus": hint, "max_results": 5}
        if tool_name == "document_rag":
            docs = [
                {
                    "document_id": f"doc-{idx}",
                    "title": doc.title,
                    "doi": None,
                    "url": None,
                    "source": doc.source,
                    "relevance_score": float(doc.relevance_score),
                }
                for idx, doc in enumerate(state.documents[:5], start=1)
            ]
            return {
                "documents": docs,
                "query": state.query,
                "top_k": 5,
                "max_documents": 5,
                "max_chunks_per_document": 20,
            }
        if tool_name == "generate_crystal_structure":
            return {"query": state.query, "format": "cif"}
        return {}

    def _extract_material_query(self, query: str) -> Dict[str, str]:
        mp_match = re.search(r"(mp-\d+)", query, flags=re.IGNORECASE)
        if mp_match:
            return {"material_id": mp_match.group(1).lower()}

        formula_match = re.search(r"\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)\b", query)
        if formula_match:
            return {"formula": formula_match.group(1)}

        return {"formula": "Si"}
