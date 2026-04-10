from __future__ import annotations

from typing import Any
import asyncio
import re

from .contracts import ToolResult
from .history_item import HistoryItem
from .runtime_state import RuntimeState
from .state import AgentState, MaterialHypothesis
from tools.validator import validate_tool_output


MAX_REPLANS = 2


def now_ms() -> int:
    import time

    return int(time.time() * 1000)


async def run_loop(state, registry, planner, evaluator, emitter, tool_catalog):
    """Execute the plan loop.

    Evaluator feedback is computed per-iteration after each successful tool
    execution. No evaluator step is run during entry-policy tool selection.
    """
    state.budget.ensure_started()
    state.sync_execution_state()

    if not state.history:
        state.history.append(
            HistoryItem(role="user", type="query", content=state.query)
        )
        state.history.append(
            HistoryItem(
                role="assistant",
                type="plan",
                content=str(state.plan.model_dump()),
                metadata={"plan": state.plan.model_dump()},
            )
        )

    while True:
        if state.budget.iterations_used >= state.budget.max_iterations:
            state.set_stop_reason("max_iterations")
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason},
                trace="Iteration budget exhausted",
            )
            break

        if state.budget.tool_calls_used >= state.budget.max_tool_calls:
            state.set_stop_reason("max_tool_calls")
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason},
                trace="Tool-call budget exhausted",
            )
            break

        if state.budget.max_wall_time_ms is not None:
            elapsed = now_ms() - int(state.budget.started_at_ms or now_ms())
            if elapsed > state.budget.max_wall_time_ms:
                state.set_stop_reason("timeout")
                await emitter.emit(
                    "stop",
                    {"reason": state.stop_reason},
                    trace="Wall-time budget exhausted",
                )
                break

        if state.plan.cursor >= len(state.plan.steps):
            state.set_stop_reason("plan_exhausted")
            state.plan.status = "exhausted"
            await emitter.emit(
                "stop", {"reason": state.stop_reason}, trace="Plan exhausted"
            )
            break

        step_idx = state.plan.cursor
        state.budget.iterations_used += 1
        state.sync_execution_state()
        step = state.plan.steps[state.plan.cursor]

        await emitter.emit(
            "tool_start",
            {"tool": step.tool, "target": step.target, "purpose": step.purpose},
            trace=f"Ejecutando {step.tool}: {step.purpose}",
        )
        state.history.append(
            HistoryItem(
                role="assistant",
                type="tool_call",
                content=f"{step.tool}:{step.target or ''}",
                metadata={
                    "tool": step.tool,
                    "target": step.target,
                    "purpose": step.purpose,
                },
            )
        )

        if not registry.can_run(step.tool, state):
            state.runtime_state.mark_step_failed(step_idx)
            state.set_stop_reason("precondition_failed")
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason, "tool": step.tool},
                trace=f"Precondition failed for {step.tool}",
            )
            break

        result = await _execute_tool(registry, state, step.tool, step.target)
        state.budget.tool_calls_used += 1
        state.sync_execution_state()

        await emitter.emit(
            "tool_result",
            {
                "status": result.status,
                "raw_output": result.raw_output,
                "structured_output": result.structured_output,
                "error_message": result.error_message,
            },
            trace="Tool execution completed",
        )
        state.history.append(
            HistoryItem(
                role="tool",
                type="tool_result",
                content=str(result.structured_output),
                metadata={
                    "tool": step.tool,
                    "status": result.status,
                    "error_message": result.error_message,
                    "raw_output": result.raw_output,
                    "structured_output": result.structured_output,
                },
            )
        )

        if result.status != "success":
            state.runtime_state.mark_step_failed(step_idx)
            state.set_stop_reason("tool_validation_failed")
            await emitter.emit(
                "stop",
                {
                    "reason": state.stop_reason,
                    "tool": step.tool,
                    "error": result.error_message,
                },
                trace="Tool execution error",
            )
            break

        state.runtime_state.mark_step_done(step_idx, step.tool)
        apply_tool_result(state, step.tool, result.structured_output)
        state.refresh_runtime_counts()

        try:
            feedback = await evaluator.evaluate(state)
        except Exception as exc:
            state.set_stop_reason("evaluator_failed")
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason, "error": str(exc)},
                trace="Evaluator failed",
            )
            break

        feedback_reason = str(
            getattr(feedback, "reason", getattr(feedback, "feedback", ""))
        ).strip()
        state.evaluations.append(feedback.model_dump())
        await emitter.emit(
            "evaluation",
            feedback.model_dump(),
            trace=feedback_reason,
        )

        if feedback.stop and feedback.constraints_ok:
            state.set_stop_reason("completed")
            state.plan.status = "completed"
            await emitter.emit(
                "stop", {"reason": state.stop_reason}, trace="Evaluator decided to stop"
            )
            break

        if feedback.modify_plan and state.replans_used < MAX_REPLANS:
            planner_outcome = await asyncio.to_thread(
                planner.build_plan,
                query=state.query,
                tool_catalog=tool_catalog,
                history=evaluator.build_history(state),
                state={
                    "cursor": state.plan.cursor,
                    "replans_used": state.replans_used,
                },
                feedback=feedback_reason,
            )
            if planner_outcome.plan is None:
                state.set_stop_reason("planner_failed")
                await emitter.emit(
                    "stop",
                    {
                        "reason": state.stop_reason,
                        "details": planner_outcome.fallback_reason,
                    },
                    trace="Planner failed during replan",
                )
                break

            state.plan = planner_outcome.plan
            state.replans_used += 1
            state.sync_execution_state()
            state.runtime_state = RuntimeState(
                plan_steps=[step.model_dump() for step in state.plan.steps]
            )
            state.refresh_runtime_counts()

            if planner_outcome.fallback_reason == "invalid_plan":
                state.constraints["invalid_plan_recovered"] = True
                state.constraints["invalid_plan_recovery_count"] = (
                    int(state.constraints.get("invalid_plan_recovery_count", 0)) + 1
                )

            state.history.append(
                HistoryItem(
                    role="assistant",
                    type="plan",
                    content=str(state.plan.model_dump()),
                    metadata={"plan": state.plan.model_dump(), "source": "replan"},
                )
            )

            await emitter.emit(
                "plan_modified",
                state.plan.model_dump(),
                trace="Plan regenerated from evaluator feedback",
            )
            continue

        state.plan.cursor += 1
        state.refresh_runtime_counts()

    if state.stop_reason is None:
        state.set_stop_reason("max_iterations")

    if state.plan.status == "active" and state.stop_reason in {
        "plan_exhausted",
        "budget_exhausted",
    }:
        state.plan.status = "exhausted"

    return state


async def _execute_tool(
    registry, state: AgentState, tool_name: str, target: str | None
) -> ToolResult:
    arguments = _build_tool_arguments(tool_name=tool_name, target=target, state=state)

    ok, error = registry.validate_input(tool_name, arguments)
    if not ok:
        return ToolResult(
            status="error",
            raw_output={"validation_stage": "input", "validation_error": error},
            structured_output={},
            error_message=f"input_validation_failed: {error}",
        )

    tool = registry.get(tool_name)

    def _run_sync() -> Any:
        return tool.execute(**arguments, agent_state=state)

    try:
        native_result = await asyncio.to_thread(_run_sync)
    except Exception as exc:
        return ToolResult(
            status="error",
            raw_output={},
            structured_output={},
            error_message=str(exc),
        )

    if getattr(native_result, "status", "error") != "success":
        return ToolResult(
            status="error",
            raw_output=getattr(native_result, "payload", {}),
            structured_output={},
            error_message=getattr(native_result, "error_detail", None)
            or getattr(native_result, "error_code", None)
            or "tool_error",
        )

    payload = getattr(native_result, "payload", {}) or {}
    out_ok, out_error = registry.validate_output(tool_name, payload)
    if not out_ok:
        return ToolResult(
            status="error",
            raw_output={"validation_stage": "output", "payload": payload},
            structured_output={},
            error_message=f"output_validation_failed: {out_error}",
        )

    tool = registry.get(tool_name)
    output_schema = getattr(tool, "output_schema", {})
    if output_schema and not validate_tool_output(payload, output_schema):
        return ToolResult(
            status="error",
            raw_output={"validation_stage": "output", "payload": payload},
            structured_output={},
            error_message="output_validation_failed: schema_mismatch",
        )

    return ToolResult(
        status="success",
        raw_output=payload,
        structured_output=payload,
        error_message=None,
    )


def _build_tool_arguments(
    tool_name: str, target: str | None, state: AgentState
) -> dict[str, Any]:
    if tool_name == "query_materials_database":
        normalized_target = (target or "").strip()
        if normalized_target and re.fullmatch(
            r"mp-\\d+", normalized_target, flags=re.IGNORECASE
        ):
            return {"material_id": normalized_target.lower(), "filters": {}, "limit": 5}
        if normalized_target:
            return {"formula": normalized_target, "filters": {}, "limit": 5}
        return {"formula": _guess_formula(state.query), "filters": {}, "limit": 5}

    if tool_name == "validate_material_constraints":
        return {"constraints": state.constraints.get("requested", state.constraints)}

    if tool_name == "search_scientific_documents":
        hint = state.hypotheses[0].formula if state.hypotheses else None
        return {"query": state.query, "material_focus": hint, "max_results": 5}

    if tool_name == "document_rag":
        documents = state.constraints.get("documents", [])
        return {
            "documents": documents[:5],
            "query": state.query,
            "top_k": 5,
            "max_documents": 5,
            "max_chunks_per_document": 20,
        }

    if tool_name == "generate_crystal_structure":
        return {"query": state.query, "format": "cif"}

    return {}


def _guess_formula(query: str) -> str:
    match = re.search(r"\\b([A-Z][a-z]?\\d*(?:[A-Z][a-z]?\\d*)+)\\b", query)
    if match:
        return match.group(1)
    return "Si"


def apply_tool_result(
    state: AgentState, tool_name: str, payload: dict[str, Any]
) -> None:
    if tool_name == "query_materials_database":
        known = {item.material_id for item in state.hypotheses}
        for row in payload.get("materials", []):
            material_id = str(row.get("material_id", "")).strip()
            if not material_id or material_id in known:
                continue
            state.hypotheses.append(
                MaterialHypothesis(
                    material_id=material_id,
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
            known.add(material_id)
        if state.hypotheses:
            state.properties_collected["materials_loaded"] = True

    elif tool_name == "validate_material_constraints":
        state.constraints["constraint_validation"] = payload
        state.properties_collected["constraint_validation"] = payload

    elif tool_name == "search_scientific_documents":
        documents = payload.get("documents", [])
        state.documents = documents if isinstance(documents, list) else []
        state.constraints["documents"] = state.documents

    elif tool_name == "document_rag":
        rag_results = payload.get("results", [])
        state.constraints["document_rag_results"] = rag_results
        state.properties_collected["document_rag_results"] = rag_results

        if isinstance(rag_results, list):
            for row in rag_results:
                if not isinstance(row, dict):
                    continue
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
        state.constraints["structure"] = payload
        state.properties_collected["structure"] = payload

    state.refresh_runtime_counts()
