import pytest

from tools.catalog.query_materials.errors import QueryValidationError
from tools.catalog.query_materials.models import MaterialRecord
from tools.catalog.query_materials.ranking import rank_materials


@pytest.fixture
def materials():
    return [
        MaterialRecord(
            material_id="mp-a",
            formula="A",
            band_gap=0.5,
            density=3.0,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.4,
            formation_energy=-0.1,
            volume=15.0,
        ),
        MaterialRecord(
            material_id="mp-b",
            formula="B",
            band_gap=1.5,
            density=5.0,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.1,
            formation_energy=-0.3,
            volume=18.0,
        ),
        MaterialRecord(
            material_id="mp-c",
            formula="C",
            band_gap=2.5,
            density=7.0,
            is_stable=False,
            is_metal=True,
            energy_above_hull=0.2,
            formation_energy=-0.2,
            volume=12.0,
        ),
    ]


def test_default_ranking_minimizes_energy_above_hull(materials):
    ranked = rank_materials(materials, None)
    assert [item.material_id for item in ranked] == ["mp-b", "mp-c", "mp-a"]


def test_weighted_ranking_with_objective(materials):
    ranked = rank_materials(
        materials,
        {
            "objective": {"band_gap": 1.5, "density": 5.0},
            "weights": {"stability": 0.5, "band_gap": 0.3, "density": 0.2},
        },
    )
    assert ranked[0].material_id == "mp-b"


def test_ranking_weights_must_sum_to_one(materials):
    with pytest.raises(QueryValidationError):
        rank_materials(
            materials,
            {
                "objective": {"band_gap": 1.0},
                "weights": {"stability": 0.5, "band_gap": 0.6},
            },
        )
