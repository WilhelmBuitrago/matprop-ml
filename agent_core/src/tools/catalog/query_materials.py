from __future__ import annotations

from typing import Any, Dict

from api.v3.state import AgentState
from tools.base import ToolContract, ToolResult


class QueryMaterialsDatabaseTool(ToolContract):
    """Query materials records with normalized response structure."""

    name = "query_materials_database"
    description = "Query materials data by material_id, formula, or chemical system."
    input_schema = {
        "type": "object",
        "properties": {
            "material_query": {
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "pattern": "^mp-\\d+$"},
                    "formula": {"type": "string"},
                    "chemical_system": {"type": "string"},
                },
                "additionalProperties": False,
                "minProperties": 1,
            },
            "filters": {
                "type": "object",
                "properties": {
                    "band_gap_min": {"type": "number"},
                    "band_gap_max": {"type": "number"},
                    "is_stable": {"type": "boolean"},
                    "is_metal": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        "required": ["material_query"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "materials": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "string"},
                        "formula": {"type": "string"},
                        "band_gap": {"type": "number"},
                        "density": {"type": "number"},
                        "is_stable": {"type": "boolean"},
                        "is_metal": {"type": "boolean"},
                    },
                    "required": [
                        "material_id",
                        "formula",
                        "band_gap",
                        "density",
                        "is_stable",
                        "is_metal",
                    ],
                    "additionalProperties": False,
                },
            },
            "count": {"type": "integer"},
        },
        "required": ["materials", "count"],
        "additionalProperties": False,
    }

    def preconditions(self, state: AgentState):
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("material_query", {})
        material_id = query.get("material_id", "mp-149")
        formula = query.get("formula", "Si")
        materials = [
            {
                "material_id": material_id,
                "formula": formula,
                "band_gap": 1.14,
                "density": 2.33,
                "is_stable": True,
                "is_metal": False,
            },
            {
                "material_id": "mp-804",
                "formula": "GaAs",
                "band_gap": 1.42,
                "density": 5.32,
                "is_stable": True,
                "is_metal": False,
            },
        ]
        return ToolResult(
            status="success", payload={"materials": materials, "count": len(materials)}
        )
