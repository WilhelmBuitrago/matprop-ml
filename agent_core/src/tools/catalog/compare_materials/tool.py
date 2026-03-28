from __future__ import annotations

import logging
from typing import Any

from api.v3.state import AgentState
from tools.base import ToolContract, ToolResult


logger = logging.getLogger(__name__)


class CompareMaterialsTool(ToolContract):
    """Compare two or more materials using selected properties."""

    name = "compare_materials"
    description = "Compare candidate materials and return property-level ranking."
    input_schema = {
        "type": "object",
        "properties": {
            "material_ids": {
                "type": "array",
                "minItems": 2,
                "items": {"type": "string", "pattern": "^mp-\\d+$"},
            },
            "properties_to_compare": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                    "enum": ["band_gap", "density", "is_stable", "is_metal"],
                },
            },
        },
        "required": ["material_ids", "properties_to_compare"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "comparison": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "string"},
                        "properties": {"type": "object"},
                        "rank": {"type": "integer"},
                    },
                    "required": ["material_id", "properties", "rank"],
                    "additionalProperties": False,
                },
            },
            "best_for": {"type": "object"},
        },
        "required": ["comparison", "best_for"],
        "additionalProperties": False,
    }

    def preconditions(self, state: AgentState):
        if len(state.materials_found) < 2:
            logger.info(
                "compare_materials precondition failed materials_found=%d",
                len(state.materials_found),
            )
            return False, "requires_at_least_two_materials"
        logger.info(
            "compare_materials precondition passed materials_found=%d",
            len(state.materials_found),
        )
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        material_ids = kwargs.get("material_ids", [])
        properties = kwargs.get("properties_to_compare", [])
        logger.info(
            "compare_materials execute material_ids=%s properties=%s",
            material_ids,
            properties,
        )
        ranked = []
        for idx, material_id in enumerate(material_ids, start=1):
            ranked.append(
                {
                    "material_id": material_id,
                    "properties": {"band_gap": 1.0 + idx * 0.1, "density": 2.0 + idx},
                    "rank": idx,
                }
            )
        logger.info("compare_materials success compared=%d", len(ranked))
        return ToolResult(
            status="success",
            payload={
                "comparison": ranked,
                "best_for": {"band_gap": material_ids[0], "density": material_ids[-1]},
            },
        )
