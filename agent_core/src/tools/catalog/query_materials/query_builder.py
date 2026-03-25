from __future__ import annotations

from typing import Any, Dict

from .errors import QueryValidationError
from .models import QueryRequest


def build_query_request(arguments: Dict[str, Any]) -> QueryRequest:
    mode_count = sum(
        1 for key in ("material_id", "formula", "chemical_system") if key in arguments
    )
    if mode_count != 1:
        raise QueryValidationError(
            "Exactly one query mode must be provided: material_id, formula, chemical_system."
        )

    if "material_id" in arguments:
        mode = "material_id"
        value = arguments["material_id"]
    elif "formula" in arguments:
        mode = "formula"
        value = arguments["formula"]
    else:
        mode = "chemical_system"
        value = arguments["chemical_system"]

    if not isinstance(value, str) or not value.strip():
        raise QueryValidationError("Query value must be a non-empty string.")

    limit = arguments.get("limit", 5)
    if not isinstance(limit, int) or not (1 <= limit <= 10):
        raise QueryValidationError("limit must be an integer between 1 and 10.")

    filters = arguments.get("filters") or {}
    if not isinstance(filters, dict):
        raise QueryValidationError("filters must be an object.")

    ranking = arguments.get("ranking")
    if ranking is not None and not isinstance(ranking, dict):
        raise QueryValidationError("ranking must be an object when provided.")

    return QueryRequest(
        mode=mode,
        value=value.strip(),
        filters=filters,
        ranking=ranking,
        limit=limit,
    )
