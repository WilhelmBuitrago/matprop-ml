from __future__ import annotations

RANGE_SCHEMA = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 2,
}

FILTERS_SCHEMA = {
    "type": "object",
    "properties": {
        "band_gap": RANGE_SCHEMA,
        "density": RANGE_SCHEMA,
        "energy_above_hull": RANGE_SCHEMA,
        "formation_energy": RANGE_SCHEMA,
        "volume": RANGE_SCHEMA,
        "is_stable": {"type": "boolean"},
        "is_metal": {"type": "boolean"},
    },
    "additionalProperties": False,
}

RANKING_SCHEMA = {
    "type": "object",
    "properties": {
        "objective": {
            "type": "object",
            "properties": {
                "band_gap": {"type": "number"},
                "density": {"type": "number"},
                "energy_above_hull": {"type": "number"},
                "formation_energy": {"type": "number"},
                "volume": {"type": "number"},
            },
            "additionalProperties": False,
        },
        "weights": {
            "type": "object",
            "properties": {
                "stability": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "band_gap": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "density": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "energy_above_hull": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "formation_energy": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "volume": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "minProperties": 1,
            "additionalProperties": False,
        },
    },
    "required": ["weights"],
    "additionalProperties": False,
}

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "material_id": {"type": "string", "pattern": "^mp-\\d+$"},
        "formula": {"type": "string", "minLength": 1},
        "chemical_system": {"type": "string", "minLength": 1},
        "filters": FILTERS_SCHEMA,
        "ranking": RANKING_SCHEMA,
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
        },
    },
    "oneOf": [
        {"required": ["material_id"]},
        {"required": ["formula"]},
        {"required": ["chemical_system"]},
    ],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
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
                    "energy_above_hull": {"type": "number"},
                    "formation_energy": {"type": "number"},
                    "volume": {"type": "number"},
                },
                "required": [
                    "material_id",
                    "formula",
                    "band_gap",
                    "density",
                    "is_stable",
                    "is_metal",
                    "energy_above_hull",
                    "formation_energy",
                    "volume",
                ],
                "additionalProperties": False,
            },
        },
        "count": {"type": "integer", "minimum": 0},
    },
    "required": ["materials", "count"],
    "additionalProperties": False,
}
