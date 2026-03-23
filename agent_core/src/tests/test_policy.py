from api.v3.policy import PolicyEngine
from api.v3.state import AgentState, BudgetState, MaterialRecord
from tools.config import TOOL_REGISTRY


def _state(query: str) -> AgentState:
    return AgentState(
        request_id="r1",
        query=query,
        intent="material_lookup",
        budget=BudgetState(
            max_iterations=8,
            max_tool_calls=8,
            max_context_tokens=2048,
            max_wall_time_ms=30000,
        ),
    )


def test_policy_selection_is_deterministic_for_same_state():
    policy = PolicyEngine()
    state = _state("find band gap for mp-149")

    d1 = policy.decide(state, TOOL_REGISTRY)
    d2 = policy.decide(state, TOOL_REGISTRY)

    assert d1.tool_name == d2.tool_name
    assert d1.tool_arguments == d2.tool_arguments


def test_policy_prefers_compare_when_two_materials_available():
    policy = PolicyEngine()
    state = _state("compare candidate materials")
    state.materials_found.append(
        MaterialRecord(material_id="mp-149", formula="Si", properties={})
    )
    state.materials_found.append(
        MaterialRecord(material_id="mp-804", formula="GaAs", properties={})
    )

    decision = policy.decide(state, TOOL_REGISTRY)

    assert decision.tool_name == "compare_materials"
