from __future__ import annotations

from typing import Dict, Any, List
import os
import time

from .policy import NoValidToolError
from .policy_engine_base import PolicyEngineBase
from .evaluator import Evaluator
from .state import (
    AgentState,
    ToolExecutionRecord,
    MaterialRecord,
    DocumentRecord,
    EvaluatorFeedback,
)
from tools.base import ToolRegistry


DEFAULT_STOP_CONFIDENCE_THRESHOLD = 0.75


def _resolve_stop_confidence_threshold() -> float:
    raw = os.getenv("AGENT_EVALUATOR_STOP_TAU", str(DEFAULT_STOP_CONFIDENCE_THRESHOLD))
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_STOP_CONFIDENCE_THRESHOLD
    return max(0.0, min(1.0, value))


def should_stop(feedback: EvaluatorFeedback, tau: float) -> bool:
    """Deterministic stop gating driven by evaluator quality signals."""
    return (
        feedback.can_answer is True
        and feedback.verdict == "sufficient"
        and feedback.confidence >= tau
        and feedback.risk_if_stop != "high"
    )


def early_stop_accuracy(correct_early_stops: int, total_early_stops: int) -> float:
    """Compute accuracy for early-stop decisions using labeled outcomes."""
    if total_early_stops <= 0:
        return 0.0
    value = correct_early_stops / total_early_stops
    return max(0.0, min(1.0, value))


def _list_available_tools(state: AgentState, registry: ToolRegistry) -> List[str]:
    return [name for name in registry.names() if registry.can_run(name, state)]


def _predict_next_planned_step(
    state: AgentState,
    policy: PolicyEngineBase,
    registry: ToolRegistry,
) -> str:
    try:
        return policy.decide(state, registry).tool_name
    except NoValidToolError:
        return "none"


def apply_tool_result(
    state: AgentState, tool_name: str, payload: Dict[str, Any]
) -> None:
    """Apply normalized tool payload to state as source of truth mutation."""
    if tool_name == "query_materials_database":
        for row in payload.get("materials", []):
            state.materials_found.append(
                MaterialRecord(
                    material_id=str(row.get("material_id", "")),
                    formula=str(row.get("formula", "")),
                    properties={
                        "band_gap": row.get("band_gap"),
                        "density": row.get("density"),
                        "is_stable": row.get("is_stable"),
                        "is_metal": row.get("is_metal"),
                        "energy_above_hull": row.get("energy_above_hull"),
                        "formation_energy": row.get("formation_energy"),
                        "volume": row.get("volume"),
                    },
                )
            )
        if state.materials_found:
            state.properties_collected["materials_loaded"] = True

    elif tool_name == "validate_material_constraints":
        state.properties_collected["constraint_validation"] = payload

    elif tool_name == "search_scientific_documents":
        for row in payload.get("documents", []):
            state.documents.append(
                DocumentRecord(
                    title=str(row.get("title", "")),
                    source=str(row.get("source", "")),
                    relevance_score=float(row.get("relevance_score", 0.0)),
                    abstract=str(row.get("abstract", "")),
                )
            )

    elif tool_name == "document_rag":
        rag_results = payload.get("results", [])
        state.properties_collected["document_rag_results"] = rag_results
        for row in rag_results:
            extracted = row.get("extracted_info", [])
            if not isinstance(extracted, list):
                continue
            cleaned = [str(item).strip() for item in extracted if str(item).strip()]
            if not cleaned:
                continue
            state.extracted_insights.append(
                {
                    "document_id": str(row.get("document_id", "")),
                    "title": str(row.get("title", "")),
                    "facts": cleaned,
                }
            )

    elif tool_name == "generate_crystal_structure":
        state.properties_collected["structure"] = payload


def run_loop(
    state: AgentState,
    policy: PolicyEngineBase,
    evaluator: Evaluator,
    registry: ToolRegistry,
) -> AgentState:
    """Run deterministic loop: policy -> tool -> update -> evaluate -> terminate checks."""
    last_tool_name = ""
    stop_tau = _resolve_stop_confidence_threshold()

    while state.can_continue():
        state.budget.iterations_used += 1

        try:
            decision = policy.decide(state, registry)
        except NoValidToolError:
            state.execution_status = "done"
            state.stop_reason = "no_valid_tools_available"
            break

        # Stall detection guards against useless repeated iterations.
        if decision.tool_name == last_tool_name:
            state.stall_counter += 1
            if state.stall_counter >= 2:
                state.execution_status = "done"
                state.stop_reason = "stall_detected"
                break
        else:
            state.stall_counter = 0
        last_tool_name = decision.tool_name

        ok, error = registry.validate_input(decision.tool_name, decision.tool_arguments)
        if not ok:
            state.execution_status = "error"
            state.stop_reason = "tool_input_validation_failed"
            state.policy_trace.append(
                {
                    "tool_name": decision.tool_name,
                    "reasoning": decision.reasoning,
                    "error": error,
                    "scores": decision.scores,
                }
            )
            break

        state.policy_trace.append(
            {
                "tool_name": decision.tool_name,
                "tool_arguments": decision.tool_arguments,
                "scores": decision.scores,
                "reasoning": decision.reasoning,
            }
        )

        started = time.perf_counter()
        tool = registry.get(decision.tool_name)
        result = tool.execute(**decision.tool_arguments, agent_state=state)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if result.status != "success":
            state.execution_status = "error"
            state.stop_reason = result.error_code or "tool_execution_failed"
            state.tool_calls.append(
                ToolExecutionRecord(
                    tool_name=decision.tool_name,
                    tool_input=decision.tool_arguments,
                    tool_output=result.payload,
                    status="error",
                    error_code=result.error_code,
                    elapsed_ms=elapsed_ms,
                )
            )
            break

        out_ok, out_error = registry.validate_output(decision.tool_name, result.payload)
        if not out_ok:
            state.execution_status = "error"
            state.stop_reason = "tool_output_validation_failed"
            state.tool_calls.append(
                ToolExecutionRecord(
                    tool_name=decision.tool_name,
                    tool_input=decision.tool_arguments,
                    tool_output={"validation_error": out_error},
                    status="error",
                    error_code="invalid_output",
                    elapsed_ms=elapsed_ms,
                )
            )
            break

        state.tool_calls.append(
            ToolExecutionRecord(
                tool_name=decision.tool_name,
                tool_input=decision.tool_arguments,
                tool_output=result.payload,
                status="success",
                error_code=None,
                elapsed_ms=elapsed_ms,
            )
        )
        state.budget.tool_calls_used += 1

        apply_tool_result(state, decision.tool_name, result.payload)

        tools_available = _list_available_tools(state, registry)
        next_planned_step = _predict_next_planned_step(state, policy, registry)

        feedback = evaluator.evaluate(
            state=state,
            tool_name=decision.tool_name,
            tool_output=result.payload,
            next_planned_step=next_planned_step,
            tools_available=tools_available,
        )
        state.evaluator_feedback.append(feedback)
        state.confidence_trajectory.append(feedback.confidence)
        state.risk_trajectory.append(feedback.risk_if_stop)
        state.evaluation_trace.append(
            {
                "step": state.budget.iterations_used,
                "tool": decision.tool_name,
                "eval": feedback.__dict__,
            }
        )

        if should_stop(feedback, stop_tau):
            state.execution_status = "done"
            state.stop_reason = "sufficient_evidence"
            break

        # Context budget is tracked each iteration to enforce hard token limits.
        evidence_text = f"{state.query}|{state.policy_trace[-1]}|{result.payload}"
        state.budget.context_tokens_used = state.approximate_tokens(evidence_text)

    if not state.stop_reason:
        state.stop_reason = "budget_exhausted"
        state.execution_status = "done"

    return state
