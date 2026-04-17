from __future__ import annotations

from typing import Any
import asyncio
import logging
import re

from contracts.tool_result import ToolSource

from .confidence import ConfidenceCalculator
from .contracts import Plan, PlanStep, ToolResult
from .history_item import HistoryItem
from .resilience_policy import ResiliencePolicy
from .runtime_state import RuntimeState
from .state import AgentState, MaterialHypothesis
from tools.validator import validate_tool_output


MAX_REPLANS = 2
logger = logging.getLogger(__name__)


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

    resilience_policy = ResiliencePolicy()
    failed_tools = int(state.constraints.get("tool_failures", 0) or 0)
    invalid_or_empty_results = int(
        state.constraints.get("invalid_or_empty_results", 0) or 0
    )

    while True:
        logger.info(
            "loop_iteration_start request_id=%s cursor=%d iteration_used=%d tool_calls_used=%d",
            state.request_id,
            state.plan.cursor,
            state.budget.iterations_used,
            state.budget.tool_calls_used,
        )
        if state.budget.iterations_used >= state.budget.max_iterations:
            state.set_stop_reason("max_iterations")
            logger.warning(
                "loop_stop request_id=%s reason=%s",
                state.request_id,
                state.stop_reason_canonical,
            )
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason},
                trace="Iteration budget exhausted",
            )
            break

        if state.budget.tool_calls_used >= state.budget.max_tool_calls:
            state.set_stop_reason("max_tool_calls")
            logger.warning(
                "loop_stop request_id=%s reason=%s",
                state.request_id,
                state.stop_reason_canonical,
            )
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
                logger.warning(
                    "loop_stop request_id=%s reason=%s",
                    state.request_id,
                    state.stop_reason_canonical,
                )
                await emitter.emit(
                    "stop",
                    {"reason": state.stop_reason},
                    trace="Wall-time budget exhausted",
                )
                break

        if state.plan.cursor >= len(state.plan.steps):
            state.set_stop_reason("plan_exhausted")
            state.plan.status = "exhausted"
            logger.warning(
                "loop_stop request_id=%s reason=%s",
                state.request_id,
                state.stop_reason_canonical,
            )
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
            logger.warning(
                "loop_stop request_id=%s reason=%s tool=%s",
                state.request_id,
                state.stop_reason_canonical,
                step.tool,
            )
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
                "payload": result.payload,
                "error_code": result.error_code,
                "error_detail": result.error_detail,
                "error_message": result.error_message,
                "confidence": result.confidence,
                "is_synthetic": result.is_synthetic,
                "trace": result.trace,
                "source": result.source,
            },
            trace="Tool execution completed",
            confidence=result.confidence,
        )
        state.history.append(
            HistoryItem(
                role="tool",
                type="tool_result",
                content=str(result.payload),
                metadata={
                    "tool": step.tool,
                    "status": result.status,
                    "source": result.source,
                    "confidence": result.confidence,
                    "is_synthetic": result.is_synthetic,
                    "trace": result.trace,
                    "error_code": result.error_code,
                    "error_detail": result.error_detail,
                    "error_message": result.error_message,
                    "payload": result.payload,
                },
            )
        )

        if result.status != "success":
            state.runtime_state.mark_step_failed(step_idx)
            failed_tools += 1
            state.constraints["tool_failures"] = failed_tools

            level3 = resilience_policy.level3_for_tool_failures(
                failed_tools=failed_tools,
                invalid_or_empty_results=invalid_or_empty_results,
            )
            if level3 is not None:
                state.constraints["resilience_level"] = level3.level
                state.constraints["resilience_action"] = level3.action
                state.constraints["resilience_reason"] = level3.reason
                state.constraints["resilience_details"] = dict(level3.details)
                state.set_stop_reason("tool_validation_failed")
                logger.warning(
                    "loop_stop request_id=%s reason=%s tool=%s error=%s",
                    state.request_id,
                    state.stop_reason_canonical,
                    step.tool,
                    result.error_message,
                )
                await emitter.emit(
                    "stop",
                    {
                        "reason": state.stop_reason,
                        "tool": step.tool,
                        "error": result.error_message,
                        "resilience": {
                            "level": level3.level,
                            "action": level3.action,
                            "details": level3.details,
                        },
                    },
                    trace="Tool execution error: direct final fallback",
                )
                break

            logger.warning(
                "loop_tool_failed_continue request_id=%s tool=%s error=%s failed_tools=%d",
                state.request_id,
                step.tool,
                result.error_message,
                failed_tools,
            )
            state.plan.cursor += 1
            state.refresh_runtime_counts()
            continue

        if _is_empty_or_invalid_payload(result.payload):
            invalid_or_empty_results += 1
            state.constraints["invalid_or_empty_results"] = invalid_or_empty_results
            level3 = resilience_policy.level3_for_tool_failures(
                failed_tools=failed_tools,
                invalid_or_empty_results=invalid_or_empty_results,
            )
            if level3 is not None:
                state.constraints["resilience_level"] = level3.level
                state.constraints["resilience_action"] = level3.action
                state.constraints["resilience_reason"] = level3.reason
                state.constraints["resilience_details"] = dict(level3.details)
                state.set_stop_reason("tool_validation_failed")
                await emitter.emit(
                    "stop",
                    {
                        "reason": state.stop_reason,
                        "tool": step.tool,
                        "resilience": {
                            "level": level3.level,
                            "action": level3.action,
                            "details": level3.details,
                        },
                    },
                    trace="Tool payload invalid/empty: direct final fallback",
                )
                break

        state.runtime_state.mark_step_done(step_idx, step.tool)
        apply_tool_result(state, step.tool, result.payload)
        state.refresh_runtime_counts()

        try:
            feedback = await evaluator.evaluate(state)
        except Exception as exc:
            state.set_stop_reason("evaluator_failed")
            logger.exception(
                "loop_stop request_id=%s reason=%s",
                state.request_id,
                state.stop_reason_canonical,
            )
            await emitter.emit(
                "stop",
                {"reason": state.stop_reason, "error": str(exc)},
                trace="Evaluator failed",
            )
            break

        feedback_reason = str(
            getattr(feedback, "reason", getattr(feedback, "feedback", ""))
        ).strip()

        if not bool(getattr(feedback, "domain_valid", True)):
            feedback.stop = False
            feedback.modify_plan = True

        state.evaluations.append(feedback.model_dump())
        await emitter.emit(
            "evaluation",
            feedback.model_dump(),
            trace=feedback_reason,
            confidence=getattr(feedback, "confidence", None),
        )
        state.history.append(
            HistoryItem(
                role="assistant",
                type="evaluation",
                content=feedback_reason,
                metadata=feedback.model_dump(),
            )
        )

        if feedback.stop and feedback.constraints_ok:
            state.set_stop_reason("completed")
            state.plan.status = "completed"
            logger.info(
                "loop_stop request_id=%s reason=%s",
                state.request_id,
                state.stop_reason_canonical,
            )
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
                level2 = resilience_policy.level2_for_planner_failure(
                    state.query,
                    planner_outcome.fallback_reason or "planner_failed",
                )
                state.plan = _build_level2_fallback_plan(
                    query=state.query,
                    selected_tool=str(level2.details.get("selected_tool", "query_materials_database")),
                )
                state.constraints["resilience_level"] = level2.level
                state.constraints["resilience_action"] = level2.action
                state.constraints["resilience_reason"] = level2.reason
                state.constraints["resilience_details"] = dict(level2.details)
                state.replans_used += 1
                state.sync_execution_state()
                state.runtime_state = RuntimeState(
                    plan_steps=[step.model_dump() for step in state.plan.steps]
                )
                state.refresh_runtime_counts()
                await emitter.emit(
                    "plan_modified",
                    {
                        "plan": state.plan.model_dump(),
                        "resilience": {
                            "level": level2.level,
                            "action": level2.action,
                            "details": level2.details,
                        },
                    },
                    trace="Planner failed during replan: deterministic fallback plan",
                )
                continue

            if planner_outcome.fallback_reason == "invalid_plan":
                level2 = resilience_policy.level2_for_planner_failure(
                    state.query,
                    "invalid_plan",
                )
                state.plan = _build_level2_fallback_plan(
                    query=state.query,
                    selected_tool=str(level2.details.get("selected_tool", "query_materials_database")),
                )
                state.constraints["resilience_level"] = level2.level
                state.constraints["resilience_action"] = level2.action
                state.constraints["resilience_reason"] = level2.reason
                state.constraints["resilience_details"] = dict(level2.details)
                state.replans_used += 1
                state.sync_execution_state()
                state.runtime_state = RuntimeState(
                    plan_steps=[step.model_dump() for step in state.plan.steps]
                )
                state.refresh_runtime_counts()
                await emitter.emit(
                    "plan_modified",
                    {
                        "plan": state.plan.model_dump(),
                        "resilience": {
                            "level": level2.level,
                            "action": level2.action,
                            "details": level2.details,
                        },
                    },
                    trace="Invalid replan recovered with deterministic fallback plan",
                )
                continue

            state.plan = planner_outcome.plan
            state.replans_used += 1
            state.sync_execution_state()
            state.runtime_state = RuntimeState(
                plan_steps=[step.model_dump() for step in state.plan.steps]
            )
            state.refresh_runtime_counts()

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
    calculator = ConfidenceCalculator()
    default_source = _default_source_for_tool(tool_name)
    default_is_synthetic = default_source in {"rag", "llm"}

    arguments = _build_tool_arguments(tool_name=tool_name, target=target, state=state)

    ok, error = registry.validate_input(tool_name, arguments)
    if not ok:
        return ToolResult(
            status="error",
            payload={"validation_stage": "input", "validation_error": error},
            error_code="INPUT_VALIDATION_ERROR",
            error_detail=f"input_validation_failed: {error}",
            confidence=0.0,
            is_synthetic=default_is_synthetic,
            trace=f"{tool_name}:input_validation",
            source=default_source,
        )

    tool = registry.get(tool_name)

    def _run_sync() -> Any:
        return tool.execute(**arguments, agent_state=state)

    try:
        native_result = await asyncio.to_thread(_run_sync)
    except Exception as exc:
        return ToolResult(
            status="error",
            payload={},
            error_code="EXECUTION_ERROR",
            error_detail=str(exc),
            confidence=0.0,
            is_synthetic=default_is_synthetic,
            trace=f"{tool_name}:exception",
            source=default_source,
        )

    if getattr(native_result, "status", "error") != "success":
        native_source = getattr(native_result, "source", default_source)
        confidence_signals = getattr(native_result, "confidence_signals", {}) or {}
        return ToolResult(
            status="error",
            payload=getattr(native_result, "payload", {}) or {},
            error_code=getattr(native_result, "error_code", None) or "TOOL_ERROR",
            error_detail=getattr(native_result, "error_detail", None),
            confidence=0.0,
            is_synthetic=bool(
                getattr(native_result, "is_synthetic", native_source in {"rag", "llm"})
            ),
            trace=getattr(native_result, "trace", None)
            or f"{tool_name}:error",
            source=native_source,
            confidence_signals=confidence_signals,
        )

    payload = getattr(native_result, "payload", {}) or {}
    out_ok, out_error = registry.validate_output(tool_name, payload)
    if not out_ok:
        return ToolResult(
            status="error",
            payload={"validation_stage": "output", "payload": payload},
            error_code="OUTPUT_VALIDATION_ERROR",
            error_detail=f"output_validation_failed: {out_error}",
            confidence=0.0,
            is_synthetic=default_is_synthetic,
            trace=f"{tool_name}:output_validation",
            source=default_source,
        )

    tool = registry.get(tool_name)
    output_schema = getattr(tool, "output_schema", {})
    if output_schema and not validate_tool_output(payload, output_schema):
        return ToolResult(
            status="error",
            payload={"validation_stage": "output", "payload": payload},
            error_code="OUTPUT_VALIDATION_ERROR",
            error_detail="output_validation_failed: schema_mismatch",
            confidence=0.0,
            is_synthetic=default_is_synthetic,
            trace=f"{tool_name}:schema_mismatch",
            source=default_source,
        )

    source = getattr(native_result, "source", default_source)
    is_synthetic = bool(
        getattr(native_result, "is_synthetic", source in {"rag", "llm"})
    )
    trace = getattr(native_result, "trace", None) or _build_default_trace(tool_name, payload)
    confidence_signals = getattr(native_result, "confidence_signals", {}) or {}
    explicit_confidence = getattr(native_result, "confidence", None)
    if isinstance(explicit_confidence, (int, float)) and explicit_confidence <= 0.0:
        explicit_confidence = None
    confidence = calculator.calculate(
        source=source,
        status="success",
        payload=payload,
        signals=confidence_signals,
        explicit_confidence=(
            float(explicit_confidence)
            if isinstance(explicit_confidence, (int, float))
            else None
        ),
    )

    return ToolResult(
        status="success",
        payload=payload,
        error_code=getattr(native_result, "error_code", None),
        error_detail=getattr(native_result, "error_detail", None),
        confidence=confidence,
        is_synthetic=is_synthetic,
        trace=trace,
        source=source,
        confidence_signals=confidence_signals,
    )


def _default_source_for_tool(tool_name: str) -> ToolSource:
    if tool_name == "query_materials_database":
        return "db"
    if tool_name == "validate_material_constraints":
        return "db"
    if tool_name == "search_scientific_documents":
        return "paper"
    if tool_name == "document_rag":
        return "rag"
    if tool_name == "generate_crystal_structure":
        return "llm"
    return "db"


def _build_default_trace(tool_name: str, payload: dict[str, Any]) -> str:
    if tool_name == "query_materials_database":
        return f"materials_count={len(payload.get('materials', []))}"
    if tool_name == "validate_material_constraints":
        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            return (
                f"passing={summary.get('passing_count', 0)};"
                f"failing={summary.get('failing_count', 0)}"
            )
    if tool_name == "search_scientific_documents":
        docs = payload.get("documents", [])
        if isinstance(docs, list):
            refs = []
            for item in docs[:5]:
                if not isinstance(item, dict):
                    continue
                ref = str(item.get("doi") or item.get("url") or item.get("document_id") or "").strip()
                if ref:
                    refs.append(ref)
            return ";".join(refs) if refs else f"documents_count={len(docs)}"
    if tool_name == "document_rag":
        results = payload.get("results", [])
        if isinstance(results, list):
            refs = []
            for item in results[:8]:
                if not isinstance(item, dict):
                    continue
                ref = str(item.get("doi") or item.get("url") or item.get("document_id") or "").strip()
                if ref:
                    refs.append(ref)
            return ";".join(refs) if refs else f"results_count={len(results)}"
    if tool_name == "generate_crystal_structure":
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict):
            return str(metadata.get("formula") or "generated_structure")
    return tool_name


def _is_empty_or_invalid_payload(payload: dict[str, Any]) -> bool:
    if not payload:
        return True
    count = payload.get("count")
    if isinstance(count, int) and count <= 0:
        return True
    for key in ("materials", "documents", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value) == 0
    return False


def _build_level2_fallback_plan(*, query: str, selected_tool: str) -> Plan:
    if selected_tool == "document_rag":
        return Plan(
            steps=[
                PlanStep(
                    tool="search_scientific_documents",
                    target=query,
                    purpose="Collect literature candidates for deterministic RAG fallback",
                ),
                PlanStep(
                    tool="document_rag",
                    target=query,
                    purpose="Extract evidence from retrieved papers in deterministic fallback",
                ),
            ],
            cursor=0,
            status="active",
        )

    return Plan(
        steps=[
            PlanStep(
                tool="query_materials_database",
                target=_guess_formula(query),
                purpose="Deterministic property lookup fallback",
            )
        ],
        cursor=0,
        status="active",
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
