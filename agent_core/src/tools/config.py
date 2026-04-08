from tools.base import ToolRegistry
from tools.catalog import (
    DocumentRAGTool,
    GenerateCrystalStructureTool,
    QueryMaterialsDatabaseTool,
    SearchScientificDocumentsTool,
    ValidateMaterialConstraintsTool,
)


"""Central v3 tool catalog and strict schema registry.

This module is the single source of truth for tool definitions, schemas, and
registration order. All policy and API layers must read tool metadata from here.
"""

TOOL_REGISTRY = ToolRegistry()
TOOL_REGISTRY.register(QueryMaterialsDatabaseTool())
TOOL_REGISTRY.register(ValidateMaterialConstraintsTool())
TOOL_REGISTRY.register(SearchScientificDocumentsTool())
TOOL_REGISTRY.register(DocumentRAGTool())
TOOL_REGISTRY.register(GenerateCrystalStructureTool())


def get_tool_catalog():
    """Return strict catalog entries with input/output schemas."""
    return TOOL_REGISTRY.as_schema_catalog()


OPENAI_FUNCTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": entry["name"],
            "description": entry["description"],
            "parameters": entry["input_schema"],
            "returns": entry["output_schema"],
        },
    }
    for entry in get_tool_catalog()
]
