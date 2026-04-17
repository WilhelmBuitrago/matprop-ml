from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from contracts.tool_result import ToolResult

if TYPE_CHECKING:
    from api.v4.state import AgentState

class ToolContract:
    """Base interface for deterministic tools."""

    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}

    def preconditions(self, state: "AgentState") -> Tuple[bool, str]:
        """Return tool availability decision and blocking reason."""
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute tool and return normalized ToolResult."""
        raise NotImplementedError


class ToolRegistry:
    """Single source of truth for registered tools and schema validation."""

    def __init__(self):
        self._tools: Dict[str, ToolContract] = {}

    def register(self, tool: ToolContract) -> None:
        self._tools[tool.name] = tool

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def get(self, tool_name: str) -> ToolContract:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        return self._tools[tool_name]

    def can_run(self, tool_name: str, state: "AgentState") -> bool:
        tool = self.get(tool_name)
        ok, _ = tool.preconditions(state)
        return ok

    def validate_input(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, str]:
        tool = self.get(tool_name)
        return self._validate_against_schema(arguments, tool.input_schema, path="$")

    def validate_output(
        self, tool_name: str, payload: Dict[str, Any]
    ) -> Tuple[bool, str]:
        tool = self.get(tool_name)
        return self._validate_against_schema(payload, tool.output_schema, path="$")

    def as_schema_catalog(self) -> List[Dict[str, Any]]:
        """Export catalog for API introspection/documentation."""
        result: List[Dict[str, Any]] = []
        for tool in self._tools.values():
            result.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema,
                }
            )
        return result

    def _validate_against_schema(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> Tuple[bool, str]:
        """Validate value against a strict subset of JSON Schema used by tools."""
        one_of = schema.get("oneOf")
        if isinstance(one_of, list):
            valid_count = 0
            last_error = ""
            for idx, candidate in enumerate(one_of):
                ok, err = self._validate_against_schema(value, candidate, path)
                if ok:
                    valid_count += 1
                else:
                    last_error = f"candidate {idx}: {err}"
            if valid_count != 1:
                return (
                    False,
                    f"{path}: expected exactly one schema in oneOf to match; "
                    f"matched={valid_count}. {last_error}",
                )

        expected_type = schema.get("type")
        if isinstance(expected_type, list):
            type_match = any(self._type_ok(value, t) for t in expected_type)
            if not type_match:
                return False, f"{path}: expected one of {expected_type}"
        elif expected_type and not self._type_ok(value, expected_type):
            return False, f"{path}: expected {expected_type}"

        if "minItems" in schema and isinstance(value, list):
            if len(value) < int(schema["minItems"]):
                return False, f"{path}: expected at least {schema['minItems']} items"

        if "maxItems" in schema and isinstance(value, list):
            if len(value) > int(schema["maxItems"]):
                return False, f"{path}: expected at most {schema['maxItems']} items"

        if "minProperties" in schema and isinstance(value, dict):
            if len(value.keys()) < int(schema["minProperties"]):
                return (
                    False,
                    f"{path}: expected at least {schema['minProperties']} properties",
                )

        if "maxProperties" in schema and isinstance(value, dict):
            if len(value.keys()) > int(schema["maxProperties"]):
                return (
                    False,
                    f"{path}: expected at most {schema['maxProperties']} properties",
                )

        if "minimum" in schema and isinstance(value, (int, float)):
            if value < float(schema["minimum"]):
                return False, f"{path}: minimum is {schema['minimum']}"

        if "maximum" in schema and isinstance(value, (int, float)):
            if value > float(schema["maximum"]):
                return False, f"{path}: maximum is {schema['maximum']}"

        enum_values = schema.get("enum")
        if enum_values is not None and value not in enum_values:
            return False, f"{path}: value {value!r} not in enum"

        if "minLength" in schema and isinstance(value, str):
            if len(value) < int(schema["minLength"]):
                return False, f"{path}: expected minLength {schema['minLength']}"

        if "maxLength" in schema and isinstance(value, str):
            if len(value) > int(schema["maxLength"]):
                return False, f"{path}: expected maxLength {schema['maxLength']}"

        pattern = schema.get("pattern")
        if pattern is not None and isinstance(value, str):
            if re.fullmatch(pattern, value) is None:
                return False, f"{path}: value {value!r} does not match pattern"

        if isinstance(value, dict):
            required = schema.get("required", [])
            for req in required:
                if req not in value:
                    return False, f"{path}: missing required field '{req}'"

            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                for key in value.keys():
                    if key not in properties:
                        return False, f"{path}: unexpected field '{key}'"

            for key, child in value.items():
                if key not in properties:
                    continue
                ok, err = self._validate_against_schema(
                    child, properties[key], f"{path}.{key}"
                )
                if not ok:
                    return False, err

        if isinstance(value, list):
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for idx, item in enumerate(value):
                    ok, err = self._validate_against_schema(
                        item, item_schema, f"{path}[{idx}]"
                    )
                    if not ok:
                        return False, err

        return True, ""

    def _type_ok(self, value: Any, expected_type: str) -> bool:
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "null":
            return value is None
        return True
