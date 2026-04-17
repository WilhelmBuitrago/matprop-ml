from __future__ import annotations

PROVIDER_ENUM = ["arxiv", "semantic_scholar", "crossref"]

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 3},
        "material_focus": {"type": ["string", "null"]},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
        "providers": {
            "type": "array",
            "items": {"type": "string", "enum": PROVIDER_ENUM},
            "minItems": 1,
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "documents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "title": {"type": "string"},
                    "authors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "year": {"type": ["integer", "null"]},
                    "source": {"type": "string"},
                    "doi": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "abstract": {"type": ["string", "null"]},
                    "relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": [
                    "document_id",
                    "title",
                    "authors",
                    "year",
                    "source",
                    "doi",
                    "url",
                    "abstract",
                    "relevance_score",
                ],
                "additionalProperties": False,
            },
        },
        "count": {"type": "integer", "minimum": 0},
        "source": {"type": "string", "enum": ["paper"]},
    },
    "required": ["documents", "count"],
    "additionalProperties": False,
}
