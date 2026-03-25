from __future__ import annotations

RANGE_SCHEMA = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 2,
}

CONSTRAINTS_SCHEMA = {
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
    "minProperties": 1,
}

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "constraints": CONSTRAINTS_SCHEMA,
    },
    "required": ["constraints"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "summary": {
            "type": "object",
            "properties": {
                "total_materials": {"type": "integer"},
                "passing_count": {"type": "integer"},
                "failing_count": {"type": "integer"},
            },
            "required": ["total_materials", "passing_count", "failing_count"],
            "additionalProperties": False,
        },
        "materials": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "material_id": {"type": "string"},
                    "passes": {"type": "boolean"},
                    "failed_constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["material_id", "passes", "failed_constraints"],
                "additionalProperties": False,
            },
        },
        "validation_errors": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["valid", "summary", "materials", "validation_errors"],
    "additionalProperties": False,
}
