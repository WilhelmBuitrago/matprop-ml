from typing import Any, Dict, List
from .state import EvalClass, EvaluationResult, Observation


class Evaluator:
    def _query_coherence_search(
        self, payload: List[Dict[str, Any]], query_text: str
    ) -> bool:
        query_low = query_text.lower()
        for item in payload[:10]:
            if not isinstance(item, dict):
                continue
            candidates = [
                str(item.get("material_id", "")).lower(),
                str(item.get("formula_pretty", "")).lower(),
                str(item.get("chemsys", "")).lower(),
            ]
            if any(candidate and candidate in query_low for candidate in candidates):
                return True
        # If query does not contain explicit material identifiers, accept as coherent.
        return not any(token in query_low for token in ["mp-", "-"])

    def _query_coherence_properties(
        self, payload: Dict[str, Any], query_text: str
    ) -> bool:
        identity = payload.get("identity", {}) if isinstance(payload, dict) else {}
        if not isinstance(identity, dict):
            return True

        query_low = query_text.lower()
        material_id = str(identity.get("material_id", "")).lower()
        formula = str(identity.get("formula_pretty", "")).lower()
        chemsys = str(identity.get("chemsys", "")).lower()
        candidates = [material_id, formula, chemsys]
        return (
            any(candidate and candidate in query_low for candidate in candidates)
            or not material_id
        )

    def evaluate(self, observation: Observation, query_text: str) -> EvaluationResult:
        # Global deterministic checks
        valid_structure = observation.payload is not None
        non_empty = observation.payload not in ({}, [], "", None)

        if observation.status != "ok":
            # Input errors are recoverable if query can be refined.
            if observation.error_code in {
                "TOOL_INPUT_ERROR",
                "TOOL_TIMEOUT",
                "TOOL_UPSTREAM_ERROR",
            }:
                return EvaluationResult(
                    klass=EvalClass.RECOVERABLE_ERROR,
                    reason_code=observation.error_code or "RECOVERABLE_ERROR",
                    details={
                        "valid_structure": valid_structure,
                        "non_empty": non_empty,
                    },
                )
            return EvaluationResult(
                klass=EvalClass.TERMINAL_ERROR,
                reason_code=observation.error_code or "TERMINAL_ERROR",
                details={"valid_structure": valid_structure, "non_empty": non_empty},
            )

        # Per-tool deterministic checks
        if observation.tool_name == "search_materials":
            return self._eval_search_materials(observation, query_text)

        if observation.tool_name == "get_material_properties":
            return self._eval_get_properties(observation, query_text)

        if not valid_structure or not non_empty:
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="EMPTY_RESULT",
                details={"valid_structure": valid_structure, "non_empty": non_empty},
            )

        return EvaluationResult(
            klass=EvalClass.SUFFICIENT,
            reason_code="GENERIC_SUFFICIENT",
            details={"valid_structure": valid_structure, "non_empty": non_empty},
        )

    def _eval_search_materials(
        self, observation: Observation, query_text: str
    ) -> EvaluationResult:
        payload = observation.payload
        if not isinstance(payload, list):
            return EvaluationResult(
                klass=EvalClass.RECOVERABLE_ERROR,
                reason_code="SEARCH_INVALID_STRUCTURE",
                details={"expected": "list"},
            )

        if len(payload) == 0:
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="SEARCH_EMPTY",
                details={"count": 0},
            )

        has_material_id = all(
            isinstance(item, dict) and item.get("material_id") for item in payload[:5]
        )
        if not has_material_id:
            return EvaluationResult(
                klass=EvalClass.RECOVERABLE_ERROR,
                reason_code="SEARCH_MISSING_MATERIAL_ID",
                details={"count": len(payload)},
            )

        is_coherent = self._query_coherence_search(payload, query_text)
        if not is_coherent:
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="SEARCH_QUERY_MISMATCH",
                details={"count": len(payload)},
            )

        return EvaluationResult(
            klass=EvalClass.SUFFICIENT,
            reason_code="SEARCH_OK",
            details={"count": len(payload), "coherent": is_coherent},
        )

    def _eval_get_properties(
        self, observation: Observation, query_text: str
    ) -> EvaluationResult:
        payload = observation.payload
        if not isinstance(payload, dict):
            return EvaluationResult(
                klass=EvalClass.RECOVERABLE_ERROR,
                reason_code="PROPERTIES_INVALID_STRUCTURE",
                details={"expected": "dict"},
            )

        if payload.get("error"):
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="PROPERTIES_NOT_FOUND",
                details={"error": payload.get("error")},
            )

        sections = ["identity", "termodynamic", "crystallography", "electronic"]
        present = [s for s in sections if s in payload and payload.get(s)]
        if not present:
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="PROPERTIES_EMPTY",
                details={"sections": present},
            )

        is_coherent = self._query_coherence_properties(payload, query_text)
        if not is_coherent:
            return EvaluationResult(
                klass=EvalClass.INSUFFICIENT,
                reason_code="PROPERTIES_QUERY_MISMATCH",
                details={"sections": present},
            )

        return EvaluationResult(
            klass=EvalClass.SUFFICIENT,
            reason_code="PROPERTIES_OK",
            details={"sections": present, "coherent": is_coherent},
        )
