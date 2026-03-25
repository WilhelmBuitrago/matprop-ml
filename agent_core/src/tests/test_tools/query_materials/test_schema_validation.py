from tools.config import TOOL_REGISTRY


def test_accepts_material_id_mode():
    ok, err = TOOL_REGISTRY.validate_input(
        "query_materials_database",
        {"material_id": "mp-149", "limit": 5},
    )
    assert ok is True
    assert err == ""


def test_rejects_multiple_query_modes():
    ok, err = TOOL_REGISTRY.validate_input(
        "query_materials_database",
        {"material_id": "mp-149", "formula": "Si"},
    )
    assert ok is False
    assert "oneOf" in err


def test_rejects_limit_out_of_range():
    ok, err = TOOL_REGISTRY.validate_input(
        "query_materials_database",
        {"formula": "Si", "limit": 11},
    )
    assert ok is False
    assert "maximum" in err or "at most" in err


def test_rejects_invalid_range_length():
    ok, err = TOOL_REGISTRY.validate_input(
        "query_materials_database",
        {"chemical_system": "Si-O", "filters": {"band_gap": [0.0, 1.0, 2.0]}},
    )
    assert ok is False
    assert "maxItems" in err or "at most" in err


def test_accepts_valid_ranking_schema():
    ok, err = TOOL_REGISTRY.validate_input(
        "query_materials_database",
        {
            "formula": "Fe2O3",
            "ranking": {
                "objective": {"band_gap": 1.5, "density": 5.0},
                "weights": {"stability": 0.5, "band_gap": 0.3, "density": 0.2},
            },
        },
    )
    assert ok is True
    assert err == ""
