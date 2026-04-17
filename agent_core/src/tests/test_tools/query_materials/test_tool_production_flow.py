import logging
import os
import importlib.util
from pathlib import Path

import pytest

from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool


pytestmark = pytest.mark.integration_docker


def _has_mp_api_key() -> bool:
    key = os.getenv("MP_API_KEY", "").strip()
    if key:
        return True

    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return False

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, value = stripped.split("=", 1)
        if k.strip() == "MP_API_KEY" and value.strip().strip('"').strip("'"):
            return True
    return False


def _has_mp_api_dependency() -> bool:
    return importlib.util.find_spec("mp_api") is not None


def test_query_materials_production_flow(caplog, tool_test_logger):
    if not _has_mp_api_key():
        pytest.skip("MP_API_KEY is required for production query_materials flow")
    if not _has_mp_api_dependency():
        pytest.skip("mp_api dependency is required for production query_materials flow")

    caplog.set_level(logging.INFO)
    tool = QueryMaterialsDatabaseTool()

    tool_test_logger.info("query_materials production_flow start material_id=mp-149")
    result = tool.execute(material_id="mp-149", limit=1)

    assert result.status == "success"
    assert "materials" in result.payload
    assert "count" in result.payload
    assert result.payload["count"] >= 1

    first = result.payload["materials"][0]
    assert first["material_id"].startswith("mp-")
    assert "formula" in first
    assert "band_gap" in first
    assert "query_materials request mode=material_id" in caplog.text
    assert "query_materials success" in caplog.text
