from __future__ import annotations

from typing import Any

from .base import ToolRegistry


def validate_tool_output(output: dict[str, Any], schema: dict[str, Any]) -> bool:
    registry = ToolRegistry()
    ok, _ = registry._validate_against_schema(output, schema, path="$")
    return ok
