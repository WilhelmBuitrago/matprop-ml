import logging
import os
from pathlib import Path

import pytest

from api.v3.state import AgentState, BudgetState, MaterialRecord
from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool
from tools.catalog.validate_material_constraints.tool import (
    ValidateMaterialConstraintsTool,
)


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


def test_validate_constraints_production_flow(caplog, tool_test_logger):
    if not _has_mp_api_key():
        pytest.skip("MP_API_KEY is required for production validation flow")

    caplog.set_level(logging.INFO)

    query_tool = QueryMaterialsDatabaseTool()
    query_result = query_tool.execute(formula="Si", limit=3)
    if query_result.status != "success" or query_result.payload.get("count", 0) == 0:
        pytest.skip("No materials returned from production Materials Project query")

    state = AgentState(
        request_id="validate-prod",
        query="validate constraints",
        intent="constraint_validation",
        budget=BudgetState(),
    )

    for row in query_result.payload["materials"]:
        state.materials_found.append(
            MaterialRecord(
                material_id=row["material_id"],
                formula=row["formula"],
                properties={
                    "band_gap": row["band_gap"],
                    "density": row["density"],
                    "is_stable": row["is_stable"],
                    "is_metal": row["is_metal"],
                    "energy_above_hull": row["energy_above_hull"],
                    "formation_energy": row["formation_energy"],
                    "volume": row["volume"],
                },
            )
        )

    constraints = {
        "band_gap": [0.0, 4.0],
        "is_metal": False,
    }

    tool = ValidateMaterialConstraintsTool()
    tool_test_logger.info(
        "validate_constraints production_flow start materials=%d constraints=%s",
        len(state.materials_found),
        sorted(constraints.keys()),
    )
    result = tool.execute(constraints=constraints, agent_state=state)

    assert result.status == "success"
    assert result.payload["summary"]["total_materials"] == len(state.materials_found)
    assert result.payload["summary"]["passing_count"] >= 0
    assert result.payload["summary"]["failing_count"] >= 0
    assert "validate_constraints success" in caplog.text
