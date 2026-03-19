import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.v2.policy import PolicyEngine
from api.v2.state import AgentState, BudgetState, ActionType
from logging import basicConfig, DEBUG
import logging

basicConfig(level=DEBUG)


def _make_state(intent: str = "material_lookup") -> AgentState:
    return AgentState(
        request_id="r1",
        query="Find material mp-149 band gap",
        intent_current=intent,
        intent_history=[intent],
        budget=BudgetState(
            max_iterations=6,
            max_tool_calls=4,
            max_context_tokens=512,
            max_wall_time_ms=30000,
            max_reclassifications=1,
            max_think_steps=1,
        ),
    )


def test_policy_initial_action_is_call_tool_for_material_lookup():
    policy = PolicyEngine()
    state = _make_state("material_lookup")

    action, reason, _, _ = policy.choose_next_action(state)

    logging.debug(f"Chosen action: {action}, Reason: {reason}")

    assert action == ActionType.CALL_TOOL
    assert reason == "INITIAL_CALL"


def test_policy_prevents_consecutive_think():
    policy = PolicyEngine()
    state = _make_state("unknown")
    state.last_action = ActionType.THINK
    state.budget.think_steps_used = 0

    action, _, _, _ = policy.choose_next_action(state)

    logging.debug(f"Chosen action: {action}")
    assert action != ActionType.THINK
