from __future__ import annotations

from typing import Any, Dict, List, Tuple

_RANGE_FIELDS = {
    "band_gap",
    "density",
    "energy_above_hull",
    "formation_energy",
    "volume",
}
_BOOL_FIELDS = {"is_stable", "is_metal"}


def validate_constraints(constraints: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate runtime logical consistency for already schema-valid constraints."""
    if not isinstance(constraints, dict):
        return False, ["constraints_must_be_object"]
    if not constraints:
        return False, ["constraints_cannot_be_empty"]

    errors: List[str] = []

    for field in _RANGE_FIELDS:
        if field not in constraints:
            continue
        value = constraints[field]
        if not isinstance(value, list) or len(value) != 2:
            errors.append(f"{field}_must_be_two_item_range")
            continue

        low, high = value
        if (
            isinstance(low, bool)
            or isinstance(high, bool)
            or not isinstance(low, (int, float))
            or not isinstance(high, (int, float))
        ):
            errors.append(f"{field}_range_values_must_be_numeric")
            continue

        if low > high:
            errors.append(f"{field}_min_greater_than_max")

    for field in _BOOL_FIELDS:
        if field in constraints and not isinstance(constraints[field], bool):
            errors.append(f"{field}_must_be_boolean")

    return len(errors) == 0, errors


def evaluate_constraints(
    material: Any, constraints: Dict[str, Any]
) -> tuple[bool, list[str]]:
    """Return whether material satisfies all constraints and list failed ones."""
    failed_constraints: list[str] = []

    properties = getattr(material, "properties", {})

    for field, condition in constraints.items():
        if field in _RANGE_FIELDS:
            value = _resolve_value(material, properties, field)
            if value is None:
                failed_constraints.append(field)
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                failed_constraints.append(field)
                continue
            low, high = condition
            if value < low or value > high:
                failed_constraints.append(field)
            continue

        if field in _BOOL_FIELDS:
            value = _resolve_value(material, properties, field)
            if value is None or not isinstance(value, bool) or value is not condition:
                failed_constraints.append(field)

    return len(failed_constraints) == 0, failed_constraints


def _resolve_value(material: Any, properties: Dict[str, Any], field: str) -> Any:
    if field in properties:
        return properties.get(field)
    return getattr(material, field, None)
