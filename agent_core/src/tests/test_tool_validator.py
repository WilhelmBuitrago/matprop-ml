from tools.validator import validate_tool_output


def test_validate_tool_output_accepts_valid_payload():
    schema = {
        "type": "object",
        "properties": {
            "materials": {"type": "array"},
            "count": {"type": "integer"},
        },
        "required": ["materials", "count"],
        "additionalProperties": False,
    }
    output = {"materials": [], "count": 0}

    assert validate_tool_output(output, schema) is True


def test_validate_tool_output_rejects_invalid_payload():
    schema = {
        "type": "object",
        "properties": {
            "materials": {"type": "array"},
            "count": {"type": "integer"},
        },
        "required": ["materials", "count"],
        "additionalProperties": False,
    }
    output = {"materials": [], "count": "zero"}

    assert validate_tool_output(output, schema) is False
