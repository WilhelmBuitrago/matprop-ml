import pytest

from tools.catalog.query_materials.errors import QueryValidationError
from tools.catalog.query_materials.filters import apply_filters
from tools.catalog.query_materials.models import MaterialRecord


@pytest.fixture
def sample_materials():
    return [
        MaterialRecord(
            material_id="mp-1",
            formula="Si",
            band_gap=1.1,
            density=2.3,
            is_stable=True,
            is_metal=False,
            energy_above_hull=0.0,
            formation_energy=-0.5,
            volume=20.0,
        ),
        MaterialRecord(
            material_id="mp-2",
            formula="Fe",
            band_gap=0.0,
            density=7.8,
            is_stable=False,
            is_metal=True,
            energy_above_hull=0.3,
            formation_energy=-0.1,
            volume=11.0,
        ),
    ]


def test_filters_are_hard_constraints(sample_materials):
    filtered = apply_filters(
        sample_materials,
        {
            "is_stable": True,
            "is_metal": False,
            "band_gap": [0.5, 2.0],
            "density": [1.0, 3.0],
        },
    )
    assert [item.material_id for item in filtered] == ["mp-1"]


def test_empty_filters_returns_original(sample_materials):
    filtered = apply_filters(sample_materials, {})
    assert [item.material_id for item in filtered] == ["mp-1", "mp-2"]


def test_invalid_range_min_gt_max_raises(sample_materials):
    with pytest.raises(QueryValidationError):
        apply_filters(sample_materials, {"band_gap": [2.0, 1.0]})
