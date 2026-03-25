from __future__ import annotations

from typing import Dict, List

from .errors import QueryValidationError
from .models import MaterialRecord

_RANGE_FIELDS = {
    "band_gap",
    "density",
    "energy_above_hull",
    "formation_energy",
    "volume",
}
_BOOL_FIELDS = {"is_stable", "is_metal"}


def apply_filters(
    materials: List[MaterialRecord], filters: Dict[str, object]
) -> List[MaterialRecord]:
    if not filters:
        return materials

    _validate_filters(filters)

    filtered: List[MaterialRecord] = []
    for material in materials:
        if _matches_filters(material, filters):
            filtered.append(material)
    return filtered


def _validate_filters(filters: Dict[str, object]) -> None:
    allowed = _RANGE_FIELDS | _BOOL_FIELDS
    unexpected = [key for key in filters if key not in allowed]
    if unexpected:
        joined = ", ".join(sorted(unexpected))
        raise QueryValidationError(f"Unsupported filter fields: {joined}")

    for key in _RANGE_FIELDS:
        if key not in filters:
            continue
        value = filters[key]
        if not isinstance(value, list) or len(value) != 2:
            raise QueryValidationError(f"Filter '{key}' must be [min, max].")
        low, high = value
        if (
            isinstance(low, bool)
            or isinstance(high, bool)
            or not isinstance(low, (int, float))
            or not isinstance(high, (int, float))
        ):
            raise QueryValidationError(f"Filter '{key}' values must be numeric.")
        if low > high:
            raise QueryValidationError(f"Filter '{key}' requires min <= max.")

    for key in _BOOL_FIELDS:
        if key in filters and not isinstance(filters[key], bool):
            raise QueryValidationError(f"Filter '{key}' must be boolean.")


def _matches_filters(material: MaterialRecord, filters: Dict[str, object]) -> bool:
    for key, value in filters.items():
        if key in _RANGE_FIELDS:
            low, high = value
            candidate = getattr(material, key)
            if candidate < low or candidate > high:
                return False
            continue

        candidate = getattr(material, key)
        if candidate is not value:
            return False

    return True
