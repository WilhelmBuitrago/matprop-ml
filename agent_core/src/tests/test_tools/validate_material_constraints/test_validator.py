from api.v3.state import AgentState, BudgetState, MaterialRecord
from tools.catalog.validate_material_constraints.tool import (
    ValidateMaterialConstraintsTool,
)
from tools.catalog.validate_material_constraints.validator import (
    evaluate_constraints,
    validate_constraints,
)


def _state() -> AgentState:
    return AgentState(
        request_id="r-constraints",
        query="validate",
        intent="material_lookup",
        budget=BudgetState(),
    )


def test_validate_constraints_rejects_min_greater_than_max():
    is_valid, errors = validate_constraints({"band_gap": [2.0, 1.0]})

    assert is_valid is False
    assert errors == ["band_gap_min_greater_than_max"]


def test_evaluate_constraints_fails_when_property_is_missing():
    material = MaterialRecord(
        material_id="mp-149",
        formula="Si",
        properties={"band_gap": 1.1},
    )

    passes, failed_constraints = evaluate_constraints(
        material,
        {"band_gap": [1.0, 2.0], "density": [1.0, 3.0]},
    )

    assert passes is False
    assert failed_constraints == ["density"]


def test_tool_returns_error_when_no_materials_in_state():
    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.constraints = {"band_gap": [0.5, 2.0]}

    result = tool.execute(constraints=state.constraints, agent_state=state)

    assert result.status == "error"
    assert result.payload == {}
    assert result.error_code == "NO_MATERIALS_IN_STATE"


def test_tool_returns_validation_error_for_invalid_constraints():
    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.materials_found.append(
        MaterialRecord(material_id="mp-149", formula="Si", properties={"band_gap": 1.1})
    )

    result = tool.execute(constraints={"band_gap": [3.0, 1.0]}, agent_state=state)

    assert result.status == "error"
    assert result.payload == {}
    assert result.error_code == "VALIDATION_ERROR"


def test_tool_evaluates_materials_deterministically():
    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.constraints = {"band_gap": [1.0, 2.0], "is_stable": True}
    state.materials_found.extend(
        [
            MaterialRecord(
                material_id="mp-149",
                formula="Si",
                properties={"band_gap": 1.1, "is_stable": True},
            ),
            MaterialRecord(
                material_id="mp-804",
                formula="GaAs",
                properties={"band_gap": 0.2, "is_stable": True},
            ),
        ]
    )

    result = tool.execute(constraints=state.constraints, agent_state=state)

    assert result.status == "success"
    assert result.payload["valid"] is True
    assert result.payload["summary"] == {
        "total_materials": 2,
        "passing_count": 1,
        "failing_count": 1,
    }
    assert result.payload["materials"] == [
        {"material_id": "mp-149", "passes": True, "failed_constraints": []},
        {
            "material_id": "mp-804",
            "passes": False,
            "failed_constraints": ["band_gap"],
        },
    ]
    assert result.payload["validation_errors"] == []
