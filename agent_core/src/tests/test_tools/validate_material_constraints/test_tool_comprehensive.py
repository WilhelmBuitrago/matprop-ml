import logging

import pytest

from api.v3.state import AgentState, BudgetState, MaterialRecord
from tools.catalog.validate_material_constraints.tool import (
    ValidateMaterialConstraintsTool,
)


pytestmark = pytest.mark.integration_docker


def _state() -> AgentState:
    return AgentState(
        request_id="constraints-tool-tests",
        query="validate",
        intent="material_lookup",
        budget=BudgetState(),
    )


def test_preconditions_enforce_constraints_and_materials(
    docker_env_for_tools,
    tool_test_logger,
):
    del docker_env_for_tools
    tool = ValidateMaterialConstraintsTool()
    state = _state()

    ok, reason = tool.preconditions(state)
    assert ok is False
    assert reason == "requires_constraints_in_state"

    state.constraints = {"band_gap": [0.5, 2.0]}
    ok, reason = tool.preconditions(state)
    assert ok is False
    assert reason == "requires_materials_in_state"

    state.materials_found.append(
        MaterialRecord(material_id="mp-149", formula="Si", properties={"band_gap": 1.1})
    )
    ok, reason = tool.preconditions(state)

    tool_test_logger.info("validate_constraints preconditions validated")
    assert ok is True
    assert reason == ""


def test_execute_requires_agent_state(docker_env_for_tools):
    del docker_env_for_tools
    tool = ValidateMaterialConstraintsTool()

    result = tool.execute(constraints={"band_gap": [0.5, 2.0]})

    assert result.status == "error"
    assert result.error_code == "AGENT_STATE_REQUIRED"
    assert result.error_detail == "agent_state must be provided for validation."


def test_execute_requires_materials_in_agent_state(docker_env_for_tools):
    del docker_env_for_tools
    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.constraints = {"band_gap": [0.5, 2.0]}

    result = tool.execute(constraints=state.constraints, agent_state=state)

    assert result.status == "error"
    assert result.error_code == "NO_MATERIALS_IN_STATE"
    assert result.error_detail == "No materials are available in agent state."


def test_execute_returns_validation_error_for_invalid_constraints(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.materials_found.append(
        MaterialRecord(material_id="mp-149", formula="Si", properties={"band_gap": 1.1})
    )

    tool_test_logger.info("validate_constraints running invalid constraints scenario")
    result = tool.execute(constraints={"density": [10.0]}, agent_state=state)

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert "density_must_be_two_item_range" in result.error_detail
    assert "validate_constraints running invalid constraints scenario" in caplog.text


def test_execute_evaluates_mixed_materials_and_reports_failures(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.constraints = {
        "band_gap": [1.0, 2.0],
        "density": [2.0, 8.0],
        "is_stable": True,
    }
    state.materials_found.extend(
        [
            MaterialRecord(
                material_id="mp-pass",
                formula="GaAs",
                properties={"band_gap": 1.42, "density": 5.32, "is_stable": True},
            ),
            MaterialRecord(
                material_id="mp-fail-gap",
                formula="Bi",
                properties={"band_gap": 0.0, "density": 9.8, "is_stable": True},
            ),
            MaterialRecord(
                material_id="mp-fail-missing",
                formula="ZnO",
                properties={"band_gap": 1.3, "is_stable": True},
            ),
        ]
    )

    tool_test_logger.info("validate_constraints evaluating mixed materials")
    result = tool.execute(constraints=state.constraints, agent_state=state)

    assert result.status == "success"
    assert result.payload["valid"] is True
    assert result.payload["summary"] == {
        "total_materials": 3,
        "passing_count": 1,
        "failing_count": 2,
    }

    by_id = {item["material_id"]: item for item in result.payload["materials"]}
    assert by_id["mp-pass"] == {
        "material_id": "mp-pass",
        "passes": True,
        "failed_constraints": [],
    }
    assert by_id["mp-fail-gap"]["passes"] is False
    assert set(by_id["mp-fail-gap"]["failed_constraints"]) == {"band_gap", "density"}
    assert by_id["mp-fail-missing"]["passes"] is False
    assert by_id["mp-fail-missing"]["failed_constraints"] == ["density"]
    assert result.payload["validation_errors"] == []
    assert "validate_constraints evaluating mixed materials" in caplog.text


def test_execute_reports_valid_false_when_no_material_passes(docker_env_for_tools):
    del docker_env_for_tools
    tool = ValidateMaterialConstraintsTool()
    state = _state()
    state.constraints = {"is_metal": False}
    state.materials_found.extend(
        [
            MaterialRecord(
                material_id="mp-1", formula="Fe", properties={"is_metal": True}
            ),
            MaterialRecord(
                material_id="mp-2", formula="Ni", properties={"is_metal": True}
            ),
        ]
    )

    result = tool.execute(constraints=state.constraints, agent_state=state)

    assert result.status == "success"
    assert result.payload["valid"] is False
    assert result.payload["summary"]["passing_count"] == 0
    assert result.payload["summary"]["failing_count"] == 2
