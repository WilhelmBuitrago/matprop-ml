import logging

import pytest

from tools.catalog.compare_materials.tool import CompareMaterialsTool


pytestmark = pytest.mark.integration_docker


def test_compare_materials_production_flow(caplog, tool_test_logger):
    caplog.set_level(logging.INFO)
    tool = CompareMaterialsTool()

    material_ids = ["mp-149", "mp-804"]
    properties = ["band_gap", "density"]

    tool_test_logger.info(
        "compare_materials production_flow start material_ids=%s properties=%s",
        material_ids,
        properties,
    )
    result = tool.execute(
        material_ids=material_ids,
        properties_to_compare=properties,
    )

    assert result.status == "success"
    assert "comparison" in result.payload
    assert "best_for" in result.payload
    assert len(result.payload["comparison"]) == len(material_ids)
    assert result.payload["comparison"][0]["material_id"] == material_ids[0]
    assert "compare_materials execute" in caplog.text
    assert "compare_materials success" in caplog.text
