from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from tools.base import ToolContract, ToolResult

from .client import MaterialsProjectClient
from .errors import QueryAPIError, QueryValidationError
from .filters import apply_filters
from .query_builder import build_query_request
from .ranking import rank_materials
from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA

if TYPE_CHECKING:
    from api.v4.state import AgentState


logger = logging.getLogger(__name__)


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
        logger.info(
            "query_materials.execute start keys=%s",
            sorted(kwargs.keys()),
        )
        try:
            if self._client is None:
                self._client = MaterialsProjectClient()
            request = build_query_request(kwargs)
            logger.info(
                "query_materials request mode=%s value=%s limit=%s filters=%s ranking=%s",
                request.mode,
                request.value,
                request.limit,
                bool(request.filters),
                bool(request.ranking),
            )
            materials = self._client.query(request)
            logger.info("query_materials fetched=%d", len(materials))
            materials = apply_filters(materials, request.filters)
            logger.info("query_materials after_filters=%d", len(materials))
            materials = rank_materials(materials, request.ranking)
            materials = materials[: request.limit]
            payload_materials = [self._material_to_payload(item) for item in materials]
            logger.info("query_materials success count=%d", len(payload_materials))
            material_ids = [
                str(item.get("material_id", "")).strip()
                for item in payload_materials
                if str(item.get("material_id", "")).strip()
            ]
            trace_value = ";".join(material_ids[:8]) or "materials_count=0"
            count = len(payload_materials)
            completeness = 1.0 if count > 0 else 0.9
            return ToolResult(
                status="success",
                payload={
                    "materials": payload_materials,
                    "count": len(payload_materials),
                    "source": "db",
                },
                source="db",
                is_synthetic=False,
                trace=trace_value,
                confidence_signals={
                    "completeness": completeness,
                    "consistency": 1.0,
                },
            )
        except QueryValidationError as exc:
            logger.warning("query_materials validation_error=%s", exc)
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail=str(exc),
                source="db",
                is_synthetic=False,
                trace="query_materials_database:validation_error",
            )
        except QueryAPIError as exc:
            logger.error("query_materials api_error=%s", exc)
            return ToolResult(
                status="error",
                payload={},
                error_code="API_ERROR",
                error_detail=str(exc),
                source="db",
                is_synthetic=False,
                trace="query_materials_database:api_error",
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("query_materials unexpected_error")
            return ToolResult(
                status="error",
                payload={},
                error_code="UNEXPECTED_ERROR",
                error_detail=str(exc),
                source="db",
                is_synthetic=False,
                trace="query_materials_database:unexpected_error",
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
