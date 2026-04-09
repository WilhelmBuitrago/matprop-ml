from __future__ import annotations

from typing import Any
import asyncio
import re

from .contracts import ToolResult
from .state import AgentState, MaterialHypothesis


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

    while True:
        if state.budget.iterations_used >= state.budget.max_iterations:
            state.stop_reason = "budget_exhausted"
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason},
                trace="Iteration budget exhausted",
            )
            break

        if state.budget.tool_calls_used >= state.budget.max_tool_calls:
            state.stop_reason = "budget_exhausted"
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason},
                trace="Tool-call budget exhausted",
            )
            break

        if state.budget.max_wall_time_ms is not None:
            elapsed = now_ms() - int(state.budget.started_at_ms or now_ms())
            if elapsed > state.budget.max_wall_time_ms:
                state.stop_reason = "budget_exhausted"
                await emitter.emit(
                    "stop",
                    {"reason": state.stop_reason},
                    trace="Wall-time budget exhausted",
                )
                break

        if state.plan.cursor >= len(state.plan.steps):
            state.stop_reason = "plan_exhausted"
            state.plan.status = "exhausted"
            await emitter.emit(
                "stop", {"reason": state.stop_reason}, trace="Plan exhausted"
            )
            break

        state.budget.iterations_used += 1
        step = state.plan.steps[state.plan.cursor]

        await emitter.emit(
            "tool_start",
            {"tool": step.tool, "target": step.target, "purpose": step.purpose},
            trace=f"Ejecutando {step.tool}: {step.purpose}",
        )

        if not registry.can_run(step.tool, state):
            state.stop_reason = "precondition_failed"
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason, "tool": step.tool},
                trace=f"Precondition failed for {step.tool}",
            )
            break

        result = await _execute_tool(registry, state, step.tool, step.target)
        state.budget.tool_calls_used += 1

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

        if result.status != "success":
            state.stop_reason = "tool_execution_failed"
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

        apply_tool_result(state, step.tool, result.structured_output)

        try:
            feedback = await evaluator.evaluate(state)
        except Exception as exc:
            state.stop_reason = "evaluator_failed"
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason, "error": str(exc)},
                trace="Evaluator failed",
            )
            break

        await emitter.emit(
            "evaluation",
            feedback.model_dump(),
            trace=feedback.feedback,
        )

        if feedback.stop and feedback.constraints_ok:
            state.stop_reason = "sufficient_evidence"
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
                feedback=feedback.feedback,
            )
            if planner_outcome.plan is None:
                state.stop_reason = "planner_failed"
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
            await emitter.emit(
                "plan_modified",
                state.plan.model_dump(),
                trace="Plan regenerated from evaluator feedback",
            )
            continue

        state.plan.cursor += 1

    if state.stop_reason is None:
        state.stop_reason = "budget_exhausted"

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
            raw_output={"validation_error": error},
            structured_output={},
            error_message=error,
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
            raw_output=payload,
            structured_output={},
            error_message=out_error,
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
