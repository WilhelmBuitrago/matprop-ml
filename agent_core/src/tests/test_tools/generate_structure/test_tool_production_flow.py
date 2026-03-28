import logging

import pytest
import requests

from tools.catalog.generate_structure.tool import GenerateCrystalStructureTool


pytestmark = pytest.mark.integration_docker


def _agents_up() -> bool:
    try:
        response = requests.get("http://agents:8003/v2/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def test_generate_structure_production_flow(caplog, tool_test_logger):
    if not _agents_up():
        pytest.skip("agents service is not reachable from agent_core container")

    caplog.set_level(logging.INFO)
    tool = GenerateCrystalStructureTool()

    query = "Generate a crystal structure for silicon in diamond cubic form"
    tool_test_logger.info("generate_structure production_flow start query=%s", query)
    result = tool.execute(
        query=query,
        format="cif",
        include_debug=True,
    )

    # Real production flow can fail due model output quality,
    # but tool must return normalized ToolResult without crashing.
    assert result.status in {"success", "error"}

    if result.status == "success":
        assert "structure" in result.payload
        assert "metadata" in result.payload
        assert "validation" in result.payload
        assert result.payload["metadata"]["output_format"] == "cif"
    else:
        assert result.error_code in {
            "VALIDATION_ERROR",
            "PARSING_ERROR",
            "GENERATION_ERROR",
        }
        assert result.error_detail

    assert "generate_structure execute start" in caplog.text
