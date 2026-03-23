from __future__ import annotations

from typing import Any

from api.v3.state import AgentState
from tools.base import ToolContract, ToolResult


class SearchScientificDocumentsTool(ToolContract):
    """Search scientific documents relevant to materials query."""

    name = "search_scientific_documents"
    description = "Search scientific literature and return ranked document metadata."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "material_focus": {"type": ["string", "null"]},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "documents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "year": {"type": "integer"},
                        "relevance_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "abstract": {"type": "string"},
                    },
                    "required": [
                        "title",
                        "source",
                        "year",
                        "relevance_score",
                        "abstract",
                    ],
                    "additionalProperties": False,
                },
            },
            "count": {"type": "integer"},
        },
        "required": ["documents", "count"],
        "additionalProperties": False,
    }

    def preconditions(self, state: AgentState):
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "materials")
        docs = [
            {
                "title": f"Band-gap engineering for {query}",
                "source": "arXiv",
                "year": 2024,
                "relevance_score": 0.91,
                "abstract": "Study on tunable semiconductor gaps.",
            },
            {
                "title": "High-throughput screening of stable semiconductors",
                "source": "ChemRxiv",
                "year": 2023,
                "relevance_score": 0.86,
                "abstract": "Large-scale screening with thermodynamic filters.",
            },
        ]
        return ToolResult(
            status="success", payload={"documents": docs, "count": len(docs)}
        )
