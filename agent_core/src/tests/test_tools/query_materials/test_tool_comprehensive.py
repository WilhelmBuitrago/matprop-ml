import logging

import pytest

from tools.catalog.query_materials.errors import QueryAPIError
from tools.catalog.query_materials.models import MaterialRecord
from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool


pytestmark = pytest.mark.integration_docker


class _FakeClient:
    def __init__(self, materials=None, error: Exception | None = None):
        self._materials = materials or []
        self._error = error
        self.calls = 0
        self.last_request = None

    def query(self, request):
        self.calls += 1
        self.last_request = request
        if self._error:
            raise self._error
        return list(self._materials)


def _sample_materials() -> list[MaterialRecord]:
    return [
        MaterialRecord(
            material_id="mp-001",
            formula="Bi2Se3",
            band_gap=1.10,
            density=7.50,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.02,
            formation_energy=-0.55,
            volume=120.0,
        ),
        MaterialRecord(
            material_id="mp-002",
            formula="Bi2Te3",
            band_gap=1.70,
            density=7.80,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.10,
            formation_energy=-0.42,
            volume=122.0,
        ),
        MaterialRecord(
            material_id="mp-003",
            formula="Bi",
            band_gap=0.00,
            density=9.80,
            is_stable=True,
            is_metal=True,
            energy_above_hull=0.00,
            formation_energy=-0.20,
            volume=130.0,
        ),
        MaterialRecord(
            material_id="mp-004",
            formula="BiO",
            band_gap=0.30,
            density=6.10,
            is_stable=False,
            is_metal=False,
            energy_above_hull=0.50,
            formation_energy=-0.10,
            volume=98.0,
        ),
    ]


def test_preconditions_always_pass(docker_env_for_tools, tool_test_logger):
    del docker_env_for_tools
    tool = QueryMaterialsDatabaseTool()

    ok, reason = tool.preconditions(state=object())
    tool_test_logger.info("query_materials preconditions validated")

    assert ok is True
    assert reason == ""


def test_execute_applies_filters_ranking_limit_and_payload_shape(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    tool = QueryMaterialsDatabaseTool()
    fake_client = _FakeClient(materials=_sample_materials())
    tool._client = fake_client

    tool_test_logger.info("query_materials executing filter/ranking/limit scenario")
    result = tool.execute(
        formula="Bi2Se3",
        limit=1,
        filters={
            "band_gap": [0.5, 2.0],
            "is_metal": False,
            "is_stable": True,
        },
        ranking={"weights": {"stability": 1.0}},
    )

    assert result.status == "success"
    assert result.payload["count"] == 1
    assert fake_client.calls == 1
    assert fake_client.last_request.mode == "formula"
    assert fake_client.last_request.value == "Bi2Se3"

    material = result.payload["materials"][0]
    assert material["material_id"] == "mp-001"
    assert set(material.keys()) == {
        "material_id",
        "formula",
        "band_gap",
        "density",
        "is_stable",
        "is_metal",
        "energy_above_hull",
        "formation_energy",
        "volume",
    }
    assert "query_materials executing filter/ranking/limit scenario" in caplog.text


def test_execute_returns_validation_error_for_invalid_query_modes(docker_env_for_tools):
    del docker_env_for_tools

    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(materials=_sample_materials())

    result = tool.execute(material_id="mp-149", formula="Si")

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert "Exactly one query mode must be provided" in result.error_detail


def test_execute_returns_validation_error_for_invalid_limit(docker_env_for_tools):
    del docker_env_for_tools

    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(materials=_sample_materials())

    result = tool.execute(formula="Si", limit=0)

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert result.error_detail == "limit must be an integer between 1 and 10."


def test_execute_maps_query_api_error_to_api_error_code(docker_env_for_tools):
    del docker_env_for_tools

    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(error=QueryAPIError("materials_project_timeout"))

    result = tool.execute(formula="Bi2Se3")

    assert result.status == "error"
    assert result.error_code == "API_ERROR"
    assert result.error_detail == "materials_project_timeout"


def test_execute_wraps_unexpected_errors(docker_env_for_tools):
    del docker_env_for_tools

    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(error=RuntimeError("unexpected_runtime_failure"))

    result = tool.execute(formula="Bi2Se3")

    assert result.status == "error"
    assert result.error_code == "UNEXPECTED_ERROR"
    assert result.error_detail == "unexpected_runtime_failure"
