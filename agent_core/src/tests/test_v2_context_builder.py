import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.v2.context_builder import ContextBuilder
from api.v2.state import AgentState, BudgetState, Observation
from logging import basicConfig, DEBUG
import logging

basicConfig(level=DEBUG)


def test_context_builder_respects_token_budget_with_compression():
    state = AgentState(
        request_id="r2",
        query="search Si materials",
        intent_current="material_lookup",
        intent_history=["material_lookup"],
        budget=BudgetState(
            max_iterations=6,
            max_tool_calls=4,
            max_context_tokens=80,
            max_wall_time_ms=30000,
            max_reclassifications=1,
            max_think_steps=1,
        ),
    )

    logging.debug(f"Initial AgentState: {state}")

    large_payload = [
        {
            "material_id": f"mp-{i}",
            "formula_pretty": "Si",
            "chemsys": "Si",
            "band_gap": i * 0.1,
            "is_metal": False,
            "noise": "x" * 200,
        }
        for i in range(20)
    ]

    logging.debug(f"Generated large payload with {len(large_payload)} items")

    state.observations.append(
        Observation(
            tool_name="search_materials",
            status="ok",
            payload=large_payload,
            elapsed_ms=20,
            query_used={"query": {"material": "Si"}},
        )
    )

    logging.debug(f"AgentState after adding observation: {state}")

    builder = ContextBuilder(max_context_tokens=80, max_items=3)
    context = builder.build(state)

    logging.debug(f"Built context: {context}")

    assert len(context) // 4 <= 80
