from dataclasses import dataclass

from tools.catalog.query_materials.models import MaterialRecord
from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool


@dataclass
class _FakeClient:
    materials: list[MaterialRecord]

    def query(self, request):
        return list(self.materials)


def _sample_materials():
    return [
        MaterialRecord(
            material_id="mp-149",
            formula="Si",
            band_gap=1.14,
            density=2.33,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.0,
            formation_energy=-0.45,
            volume=20.1,
        ),
        MaterialRecord(
            material_id="mp-804",
            formula="GaAs",
            band_gap=1.42,
            density=5.32,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.05,
            formation_energy=-0.3,
            volume=45.0,
        ),
    ]


def test_tool_executes_filter_rank_and_limit():
    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(_sample_materials())

    result = tool.execute(
        formula="Si",
        limit=1,
        filters={"density": [0.0, 10.0], "is_metal": False},
        ranking={"weights": {"stability": 1.0}},
    )

    assert result.status == "success"
    assert result.payload["count"] == 1
    assert len(result.payload["materials"]) == 1


def test_tool_returns_success_with_empty_result_set():
    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient([])

    result = tool.execute(formula="Si", limit=5)

    assert result.status == "success"
    assert result.payload == {"materials": [], "count": 0, "source": "db"}


def test_tool_returns_validation_error_for_invalid_runtime_ranking_sum():
    tool = QueryMaterialsDatabaseTool()
    tool._client = _FakeClient(_sample_materials())

    result = tool.execute(
        formula="Si",
        ranking={"weights": {"stability": 0.8, "band_gap": 0.3}},
    )

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert result.payload == {}
