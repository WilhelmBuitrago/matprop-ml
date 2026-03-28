from __future__ import annotations

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "documents": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "doi": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "source": {"type": "string", "minLength": 1},
                    "relevance_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": [
                    "document_id",
                    "title",
                    "doi",
                    "url",
                    "source",
                    "relevance_score",
                ],
                "additionalProperties": False,
            },
        },
        "query": {"type": "string", "minLength": 3},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        "max_documents": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        "max_chunks_per_document": {
            "type": "integer",
            "minimum": 5,
            "maximum": 50,
            "default": 20,
        },
    },
    "required": ["documents", "query"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "doi": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "title": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "section": {"type": "string"},
                    "paragraph": {"type": "string"},
                    "chunk": {"type": "string"},
                    "score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "extracted_info": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "document_id",
                    "doi",
                    "url",
                    "title",
                    "page",
                    "section",
                    "paragraph",
                    "chunk",
                    "score",
                    "extracted_info",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}
