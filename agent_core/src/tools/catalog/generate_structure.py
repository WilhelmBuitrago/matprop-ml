from __future__ import annotations

from typing import Any

from api.v3.state import AgentState
from tools.base import ToolContract, ToolResult


class GenerateCrystalStructureTool(ToolContract):
    """Generate structure representation for selected material."""

    name = "generate_crystal_structure"
    description = "Generate normalized crystal structure output in requested format."
    input_schema = {
        "type": "object",
        "properties": {
            "material_id": {"type": "string", "pattern": "^mp-\\d+$"},
            "format": {"type": "string", "enum": ["cif", "poscar", "json"]},
        },
        "required": ["material_id"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "material_id": {"type": "string"},
            "structure_data": {"type": "string"},
            "structure_format": {"type": "string"},
            "lattice_parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                    "c": {"type": "number"},
                    "alpha": {"type": "number"},
                    "beta": {"type": "number"},
                    "gamma": {"type": "number"},
                },
                "required": ["a", "b", "c", "alpha", "beta", "gamma"],
                "additionalProperties": False,
            },
        },
        "required": [
            "material_id",
            "structure_data",
            "structure_format",
            "lattice_parameters",
        ],
        "additionalProperties": False,
    }

    def preconditions(self, state: AgentState):
        if not state.materials_found:
            return False, "requires_material_in_state"
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        material_id = kwargs.get("material_id", "mp-149")
        output_format = kwargs.get("format", "cif")
        cif_stub = (
            "data_mp_149\\n"
            "_symmetry_space_group_name_H-M   'Fd-3m'\\n"
            "_cell_length_a   5.431\\n"
        )
        return ToolResult(
            status="success",
            payload={
                "material_id": material_id,
                "structure_data": (
                    cif_stub if output_format == "cif" else '{"sites": []}'
                ),
                "structure_format": output_format,
                "lattice_parameters": {
                    "a": 5.431,
                    "b": 5.431,
                    "c": 5.431,
                    "alpha": 90.0,
                    "beta": 90.0,
                    "gamma": 90.0,
                },
            },
        )
