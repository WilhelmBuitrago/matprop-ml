import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.v2.evaluator import Evaluator
from api.v2.state import Observation, EvalClass
from logging import basicConfig, DEBUG
import logging

basicConfig(level=DEBUG)


def test_evaluator_search_sufficient_when_material_ids_present():
    evaluator = Evaluator()
    obs = Observation(
        tool_name="search_materials",
        status="ok",
        payload=[
            {
                "material_id": "mp-149",
                "formula_pretty": "Si",
                "chemsys": "Si",
            }
        ],
        elapsed_ms=10,
    )

    logging.debug(f"Observation: {obs}")

    result = evaluator.evaluate(obs, "find mp-149")

    logging.debug(f"Evaluation result: {result}")

    assert result.klass == EvalClass.SUFFICIENT
    assert result.reason_code == "SEARCH_OK"


def test_evaluator_properties_insufficient_when_empty_sections():
    evaluator = Evaluator()
    obs = Observation(
        tool_name="get_material_properties",
        status="ok",
        payload={"identity": {}},
        elapsed_ms=12,
    )

    logging.debug(f"Observation: {obs}")

    result = evaluator.evaluate(obs, "band gap of Si")

    logging.debug(f"Evaluation result: {result}")

    assert result.klass == EvalClass.INSUFFICIENT
    assert result.reason_code == "PROPERTIES_EMPTY"
