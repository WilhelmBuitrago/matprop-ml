from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tools.base import ToolContract, ToolResult

from .client import MaterialsProjectClient
from .errors import QueryAPIError, QueryValidationError
from .filters import apply_filters
from .query_builder import build_query_request
from .ranking import rank_materials
from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA

if TYPE_CHECKING:
    from api.v3.state import AgentState


class QueryMaterialsDatabaseTool(ToolContract):
    """Query materials records with deterministic filtering and ranking."""

    name = "query_materials_database"
    description = "Query materials by material_id, formula, or chemical system."
    input_schema = INPUT_SCHEMA
    output_schema = OUTPUT_SCHEMA

    def __init__(self) -> None:
        self._client: MaterialsProjectClient | None = None

    def preconditions(self, state: "AgentState"):
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            if self._client is None:
                self._client = MaterialsProjectClient()
            request = build_query_request(kwargs)
            materials = self._client.query(request)
            materials = apply_filters(materials, request.filters)
            materials = rank_materials(materials, request.ranking)
            materials = materials[: request.limit]
            payload_materials = [self._material_to_payload(item) for item in materials]
            return ToolResult(
                status="success",
                payload={
                    "materials": payload_materials,
                    "count": len(payload_materials),
                },
            )
        except QueryValidationError as exc:
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail=str(exc),
            )
        except QueryAPIError as exc:
            return ToolResult(
                status="error",
                payload={},
                error_code="API_ERROR",
                error_detail=str(exc),
            )
        except Exception as exc:  # pragma: no cover
            return ToolResult(
                status="error",
                payload={},
                error_code="UNEXPECTED_ERROR",
                error_detail=str(exc),
            )

    @staticmethod
    def _material_to_payload(material) -> dict:
        return {
            "material_id": material.material_id,
            "formula": material.formula,
            "band_gap": material.band_gap,
            "density": material.density,
            "is_stable": material.is_stable,
            "is_metal": material.is_metal,
            "energy_above_hull": material.energy_above_hull,
            "formation_energy": material.formation_energy,
            "volume": material.volume,
        }
