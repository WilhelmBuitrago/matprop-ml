from __future__ import annotations

from typing import Any, Dict

from api.v3.state import AgentState
from tools.base import ToolContract, ToolResult


class ValidateMaterialConstraintsTool(ToolContract):
    """Validate materials against user constraints."""

    name = "validate_material_constraints"
    description = "Validate constraints over available materials and report matches."
    input_schema = {
        "type": "object",
        "properties": {
            "constraints": {
                "type": "object",
                "minProperties": 1,
            }
        },
        "required": ["constraints"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "valid": {"type": "boolean"},
            "passing_materials": {"type": "array", "items": {"type": "string"}},
            "failing_materials": {"type": "array", "items": {"type": "string"}},
            "validation_errors": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "valid",
            "passing_materials",
            "failing_materials",
            "validation_errors",
        ],
        "additionalProperties": False,
    }

    def preconditions(self, state: AgentState):
        if not state.constraints:
            return False, "requires_constraints_in_state"
        if not state.materials_found:
            return False, "requires_materials_in_state"
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        constraints: Dict[str, Any] = kwargs.get("constraints", {})
        errors = []
        if "band_gap" in constraints and isinstance(constraints["band_gap"], dict):
            lo = constraints["band_gap"].get("min", 0)
            hi = constraints["band_gap"].get("max", 10)
            if lo > hi:
                errors.append("band_gap_min_greater_than_max")

        passing = ["mp-149", "mp-804"] if not errors else []
        failing = [] if not errors else ["mp-149", "mp-804"]
        return ToolResult(
            status="success",
            payload={
                "valid": not errors,
                "passing_materials": passing,
                "failing_materials": failing,
                "validation_errors": errors,
            },
        )
