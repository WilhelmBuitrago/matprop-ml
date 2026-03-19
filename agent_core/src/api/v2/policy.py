from typing import Dict, List, Optional, Tuple
import re
from .state import ActionType, AgentState, EvalClass


INTENT_ACTION_MASK: Dict[str, List[ActionType]] = {
    "material_lookup": [
        ActionType.CALL_TOOL,
        ActionType.RETRY_TOOL,
        ActionType.REFINE_QUERY,
        ActionType.RECLASSIFY_INTENT,
        ActionType.THINK,
        ActionType.DELEGATE_TO_REASONER,
        ActionType.FINALIZE_FAILURE,
    ],
    "property_lookup": [
        ActionType.CALL_TOOL,
        ActionType.RETRY_TOOL,
        ActionType.REFINE_QUERY,
        ActionType.RECLASSIFY_INTENT,
        ActionType.THINK,
        ActionType.DELEGATE_TO_REASONER,
        ActionType.FINALIZE_FAILURE,
    ],
    "explanation_only": [
        ActionType.THINK,
        ActionType.RECLASSIFY_INTENT,
        ActionType.DELEGATE_TO_REASONER,
        ActionType.FINALIZE_FAILURE,
    ],
    "unknown": [
        ActionType.THINK,
        ActionType.REFINE_QUERY,
        ActionType.RECLASSIFY_INTENT,
        ActionType.CALL_TOOL,
        ActionType.DELEGATE_TO_REASONER,
        ActionType.FINALIZE_FAILURE,
    ],
}

INTENT_TOOL_PRIORITY: Dict[str, List[str]] = {
    "material_lookup": ["search_materials", "get_material_properties"],
    "property_lookup": ["search_materials", "get_material_properties"],
    "explanation_only": [],
    "unknown": ["search_materials", "get_material_properties"],
}

INTENT_STOP_POLICY: Dict[str, Dict[str, int]] = {
    "material_lookup": {"min_success_observations": 1},
    "property_lookup": {"min_success_observations": 2},
    "explanation_only": {"min_success_observations": 0},
    "unknown": {"min_success_observations": 1},
}

PROPERTY_KEYWORDS = {
    "band gap": "band_gap",
    "band_gap": "band_gap",
    "efermi": "efermi",
    "metal": "is_metal",
    "density": "density",
    "volume": "volume",
    "stable": "is_stable",
    "formation": "formation_energy_per_atom",
    "hull": "energy_above_hull",
}


class PolicyEngine:
    def classify_intent(self, prompt: str) -> str:
        p = prompt.lower()
        if any(k in p for k in ["explain", "what is", "how does"]):
            return "explanation_only"
        if any(k in p for k in ["property", "band gap", "efermi", "density", "stable"]):
            return "property_lookup"
        if any(k in p for k in ["find", "search", "material", "mp-"]):
            return "material_lookup"
        return "unknown"

    def extract_material_hint(self, prompt: str) -> Optional[str]:
        mp_match = re.search(r"(mp-\d+)", prompt, flags=re.IGNORECASE)
        if mp_match:
            return mp_match.group(1).lower()

        chemsys_match = re.search(r"\b([A-Z][a-z]?(?:-[A-Z][a-z]?)+)\b", prompt)
        if chemsys_match:
            return chemsys_match.group(1)

        formula_match = re.search(r"\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)\b", prompt)
        if formula_match:
            return formula_match.group(1)

        return None

    def extract_property_list(self, prompt: str) -> List[str]:
        prompt_low = prompt.lower()
        found: List[str] = []
        for key, normalized in PROPERTY_KEYWORDS.items():
            if key in prompt_low and normalized not in found:
                found.append(normalized)
        if not found:
            found = ["band_gap", "is_metal", "density"]
        return found

    def action_mask(self, intent: str) -> List[ActionType]:
        return INTENT_ACTION_MASK.get(intent, INTENT_ACTION_MASK["unknown"])

    def tool_priority(self, intent: str) -> List[str]:
        return INTENT_TOOL_PRIORITY.get(intent, INTENT_TOOL_PRIORITY["unknown"])

    def stop_threshold(self, intent: str) -> int:
        cfg = INTENT_STOP_POLICY.get(intent, INTENT_STOP_POLICY["unknown"])
        return cfg.get("min_success_observations", 1)

    def choose_next_action(
        self, state: AgentState
    ) -> Tuple[ActionType, str, List[ActionType], List[str]]:
        allowed = self.action_mask(state.intent_current)
        tool_priority = self.tool_priority(state.intent_current)
        last_eval = state.evaluations[-1] if state.evaluations else None
        previous_was_think = state.last_action == ActionType.THINK

        if state.budget is None:
            return ActionType.FINALIZE_FAILURE, "MISSING_BUDGET", allowed, tool_priority

        if state.elapsed_ms() >= state.budget.max_wall_time_ms:
            return ActionType.FINALIZE_FAILURE, "MAX_WALL_TIME", allowed, tool_priority
        if state.budget.iterations_used >= state.budget.max_iterations:
            return ActionType.FINALIZE_FAILURE, "MAX_ITERATIONS", allowed, tool_priority
        if state.budget.tool_calls_used >= state.budget.max_tool_calls:
            return (
                ActionType.DELEGATE_TO_REASONER,
                "MAX_TOOL_CALLS",
                allowed,
                tool_priority,
            )

        successful_obs = sum(
            1 for ev in state.evaluations if ev.klass == EvalClass.SUFFICIENT
        )
        if successful_obs >= self.stop_threshold(state.intent_current):
            return (
                ActionType.DELEGATE_TO_REASONER,
                "ENOUGH_EVIDENCE",
                allowed,
                tool_priority,
            )

        if last_eval is None:
            if (
                ActionType.CALL_TOOL in allowed
                and state.intent_current != "explanation_only"
            ):
                return ActionType.CALL_TOOL, "INITIAL_CALL", allowed, tool_priority
            if (
                ActionType.THINK in allowed
                and state.budget.think_steps_used < state.budget.max_think_steps
                and not previous_was_think
            ):
                return ActionType.THINK, "INITIAL_THINK", allowed, tool_priority
            return (
                ActionType.DELEGATE_TO_REASONER,
                "INITIAL_DELEGATE",
                allowed,
                tool_priority,
            )

        if last_eval.klass == EvalClass.SUFFICIENT:
            return (
                ActionType.DELEGATE_TO_REASONER,
                "LAST_STEP_SUFFICIENT",
                allowed,
                tool_priority,
            )

        if last_eval.klass == EvalClass.RECOVERABLE_ERROR:
            if ActionType.RETRY_TOOL in allowed and state.last_tool_name:
                return (
                    ActionType.RETRY_TOOL,
                    "RECOVERABLE_RETRY",
                    allowed,
                    tool_priority,
                )
            if ActionType.REFINE_QUERY in allowed:
                return (
                    ActionType.REFINE_QUERY,
                    "RECOVERABLE_REFINE",
                    allowed,
                    tool_priority,
                )

        if last_eval.klass == EvalClass.INSUFFICIENT:
            if (
                ActionType.THINK in allowed
                and state.budget.think_steps_used < state.budget.max_think_steps
                and not previous_was_think
            ):
                return ActionType.THINK, "INSUFFICIENT_THINK", allowed, tool_priority
            if (
                ActionType.CALL_TOOL in allowed
                and state.budget.tool_calls_used < state.budget.max_tool_calls
            ):
                return (
                    ActionType.CALL_TOOL,
                    "INSUFFICIENT_MORE_EVIDENCE",
                    allowed,
                    tool_priority,
                )

        if (
            ActionType.RECLASSIFY_INTENT in allowed
            and state.budget.reclassifications_used < state.budget.max_reclassifications
        ):
            return (
                ActionType.RECLASSIFY_INTENT,
                "STRATEGY_SHIFT",
                allowed,
                tool_priority,
            )

        if ActionType.DELEGATE_TO_REASONER in allowed:
            return (
                ActionType.DELEGATE_TO_REASONER,
                "FALLBACK_DELEGATE",
                allowed,
                tool_priority,
            )

        return ActionType.FINALIZE_FAILURE, "NO_VALID_ACTION", allowed, tool_priority
