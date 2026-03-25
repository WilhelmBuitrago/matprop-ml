from __future__ import annotations

from typing import Dict, List, Tuple

from .errors import QueryValidationError
from .models import MaterialRecord, RankedMaterial

DEFAULT_MISSING_ENERGY_PENALTY = -1_000_000_000.0
_NUMERIC_FIELDS = {
    "band_gap",
    "density",
    "energy_above_hull",
    "formation_energy",
    "volume",
}
_MINIMIZE_WHEN_NO_TARGET = {"energy_above_hull", "formation_energy"}


def rank_materials(
    materials: List[MaterialRecord], ranking_config: Dict[str, object] | None
) -> List[MaterialRecord]:
    if not materials:
        return []

    if ranking_config is None:
        ranked = [
            RankedMaterial(material=item, score=_default_score(item))
            for item in materials
        ]
        ranked.sort(key=lambda entry: entry.score, reverse=True)
        return [entry.material for entry in ranked]

    weights = ranking_config.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise QueryValidationError("ranking.weights is required and must be an object.")

    objective = ranking_config.get("objective")
    if objective is None:
        objective = {}
    if not isinstance(objective, dict):
        raise QueryValidationError("ranking.objective must be an object when provided.")

    _validate_weights(weights)
    _validate_objective(objective)

    bounds = _compute_bounds(materials, weights, objective)

    ranked: List[RankedMaterial] = []
    for material in materials:
        score = compute_score(material, objective, weights, bounds)
        ranked.append(RankedMaterial(material=material, score=score))

    ranked.sort(key=lambda entry: entry.score, reverse=True)
    return [entry.material for entry in ranked]


def compute_score(
    material: MaterialRecord,
    objective: Dict[str, float],
    weights: Dict[str, float],
    bounds: Dict[str, Tuple[float, float]],
) -> float:
    score = 0.0
    for key, raw_weight in weights.items():
        weight = float(raw_weight)

        if key == "stability":
            score += weight * _stability_component(material)
            continue

        if key not in _NUMERIC_FIELDS:
            raise QueryValidationError(f"Unsupported ranking weight key: {key}")

        normalized_value = _normalize_value(getattr(material, key), bounds[key])
        if key in objective:
            target_norm = _normalize_value(float(objective[key]), bounds[key])
            component = -abs(normalized_value - target_norm)
        elif key in _MINIMIZE_WHEN_NO_TARGET:
            component = 1.0 - normalized_value
        else:
            component = normalized_value

        score += weight * component

    return score


def _default_score(material: MaterialRecord) -> float:
    energy = material.energy_above_hull
    if energy is None:
        return DEFAULT_MISSING_ENERGY_PENALTY
    return -float(energy)


def _stability_component(material: MaterialRecord) -> float:
    if material.energy_above_hull is None:
        return DEFAULT_MISSING_ENERGY_PENALTY
    return -float(material.energy_above_hull)


def _compute_bounds(
    materials: List[MaterialRecord],
    weights: Dict[str, float],
    objective: Dict[str, float],
) -> Dict[str, Tuple[float, float]]:
    keys = set(objective.keys())
    keys.update(key for key in weights.keys() if key in _NUMERIC_FIELDS)

    bounds: Dict[str, Tuple[float, float]] = {}
    for key in keys:
        values = [float(getattr(material, key)) for material in materials]
        lower = min(values)
        upper = max(values)
        bounds[key] = (lower, upper)
    return bounds


def _normalize_value(value: float, bounds: Tuple[float, float]) -> float:
    lower, upper = bounds
    span = upper - lower
    if span == 0:
        return 0.5
    return (float(value) - lower) / span


def _validate_weights(weights: Dict[str, float]) -> None:
    total = 0.0
    for key, value in weights.items():
        if key != "stability" and key not in _NUMERIC_FIELDS:
            raise QueryValidationError(f"Unsupported ranking weight key: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QueryValidationError("ranking.weights values must be numeric.")
        if value < 0.0:
            raise QueryValidationError("ranking.weights values must be >= 0.")
        total += float(value)

    if abs(total - 1.0) > 1e-9:
        raise QueryValidationError("ranking.weights must sum to 1.0 exactly.")


def _validate_objective(objective: Dict[str, float]) -> None:
    for key, value in objective.items():
        if key not in _NUMERIC_FIELDS:
            raise QueryValidationError(f"Unsupported ranking objective key: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QueryValidationError("ranking.objective values must be numeric.")
