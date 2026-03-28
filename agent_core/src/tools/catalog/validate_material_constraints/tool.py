from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from tools.base import ToolContract, ToolResult

from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA
from .validator import evaluate_constraints, validate_constraints

if TYPE_CHECKING:
    from api.v3.state import AgentState


logger = logging.getLogger(__name__)


class ValidateMaterialConstraintsTool(ToolContract):
    """Validate and evaluate constraints against materials present in state."""

    name = "validate_material_constraints"
    description = (
        "Validate and evaluate constraints against materials present "
        "in the agent state."
    )
    input_schema = INPUT_SCHEMA
    output_schema = OUTPUT_SCHEMA

    def preconditions(self, state: "AgentState"):
        if not state.constraints:
            return False, "requires_constraints_in_state"
        if not state.materials_found:
            return False, "requires_materials_in_state"
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        state = kwargs.get("agent_state")
        constraints: Dict[str, Any] = kwargs.get("constraints", {})
        logger.info(
            "validate_constraints execute constraints_keys=%s",
            sorted(constraints.keys()),
        )

        if state is None:
            logger.warning("validate_constraints missing agent_state")
            return ToolResult(
                status="error",
                payload={},
                error_code="AGENT_STATE_REQUIRED",
                error_detail="agent_state must be provided for validation.",
            )

        materials = getattr(state, "materials_found", None)
        if not materials:
            logger.warning("validate_constraints no materials in state")
            return ToolResult(
                status="error",
                payload={},
                error_code="NO_MATERIALS_IN_STATE",
                error_detail="No materials are available in agent state.",
            )

        valid_constraints, validation_errors = validate_constraints(constraints)
        if not valid_constraints:
            logger.warning(
                "validate_constraints invalid constraints errors=%s",
                validation_errors,
            )
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="; ".join(validation_errors),
            )

        material_results = []
        passing_count = 0

        for material in materials:
            passes, failed_constraints = evaluate_constraints(material, constraints)
            if passes:
                passing_count += 1
            material_results.append(
                {
                    "material_id": str(getattr(material, "material_id", "")),
                    "passes": passes,
                    "failed_constraints": failed_constraints,
                }
            )

        total_materials = len(material_results)
        failing_count = total_materials - passing_count

        payload = {
            "valid": passing_count > 0,
            "summary": {
                "total_materials": total_materials,
                "passing_count": passing_count,
                "failing_count": failing_count,
            },
            "materials": material_results,
            "validation_errors": [],
        }
        logger.info(
            "validate_constraints success total=%d passing=%d failing=%d",
            total_materials,
            passing_count,
            failing_count,
        )
        return ToolResult(status="success", payload=payload)
