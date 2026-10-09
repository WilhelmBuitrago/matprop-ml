from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Tuple


FLOW_VALID_STOP_REASONS = {
    "sufficient_evidence",
    "budget_exhausted",
    "no_valid_tools_available",
    "stall_detected",
    "tool_input_validation_failed",
    "tool_output_validation_failed",
    # Legacy compatibility
    "sufficient_answer",
    "controlled_failure",
    # Budget-stop compatibility (legacy and current)
    "max_iterations",
    "max_tool_calls",
    "max_wall_time_ms",
    "max_context_tokens",
    "invalid_response",
    "timeout",
}

FLOW_LOOP_FAILURE_REASONS = {
    "budget_exhausted",
    "stall_detected",
    "tool_input_validation_failed",
    "tool_output_validation_failed",
    "max_iterations",
    "max_tool_calls",
    "max_wall_time_ms",
    "max_context_tokens",
    "invalid_response",
    "timeout",
}

FLOW_FALLBACK_REASONS = {
    "budget_exhausted",
    "no_valid_tools_available",
    "stall_detected",
    # Legacy compatibility
    "controlled_failure",
}

FLOW_SUCCESS_REASON = "sufficient_evidence"


def compute_flow_metrics(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    queries = run_payload.get("queries", [])
    manifest = run_payload.get("manifest", {})

    query_reports: List[Dict[str, Any]] = []

    weights: List[float] = []
    success_flags: List[int] = []
    false_success_flags: List[int] = []
    fallback_flags: List[int] = []
    loop_failure_flags: List[int] = []
    tool_efficiency_scores: List[float] = []
    reasoning_stability_scores: List[float] = []
    tool_misuse_scores: List[float] = []

    iterations_values: List[float] = []
    tool_calls_values: List[float] = []
    reclass_values: List[float] = []
    latency_values: List[float] = []

    validation_failures: List[Dict[str, Any]] = []

    for query_item in queries:
        primary = query_item.get("primary_repeat", {})
        repeats = query_item.get("repeats", [])
        metadata = primary.get("metadata", {}) or {}
        data_quality = primary.get("data_quality", {}) or {}
        stop_reason = str(primary.get("stop_reason", "unknown"))
        expected_tools = query_item.get("expected_tools", [])
        tools_used = primary.get("tools_used", [])
        weight = float(query_item.get("weight", 1.0))

        flow_eval = _evaluate_flow_query(query_item)

        tool_analysis = _analyze_tool_efficiency(
            tools_used, expected_tools, stop_reason
        )
        stability = _compute_reasoning_stability(repeats)
        weights.append(weight)
        success_flags.append(1 if flow_eval["success"] else 0)
        false_success_flags.append(1 if flow_eval["false_success"] else 0)
        fallback_flags.append(1 if stop_reason in FLOW_FALLBACK_REASONS else 0)
        loop_failure_flags.append(1 if stop_reason in FLOW_LOOP_FAILURE_REASONS else 0)
        tool_efficiency_scores.append(tool_analysis["efficiency"])
        reasoning_stability_scores.append(stability["stability_score"])
        tool_misuse_scores.append(tool_analysis["misuse_score"])

        iterations_values.append(float(metadata.get("iterations_count", 0)))
        tool_calls_values.append(float(metadata.get("tool_calls_count", 0)))
        reclass_values.append(float(metadata.get("reclassifications_count", 0)))
        latency_values.append(float(metadata.get("elapsed_ms", 0)))

        query_reports.append(
            {
                "case_id": query_item.get("case_id"),
                "query": query_item.get("query"),
                "difficulty": query_item.get("difficulty"),
                "weight": weight,
                "stop_reason": stop_reason,
                "success": flow_eval["success"],
                "false_success": flow_eval["false_success"],
                "flow_evaluator": flow_eval,
                "tool_efficiency": tool_analysis,
                "reasoning_stability": stability,
                "execution": {
                    "iterations_count": metadata.get("iterations_count", 0),
                    "tool_calls_count": metadata.get("tool_calls_count", 0),
                    "reclassifications_count": metadata.get(
                        "reclassifications_count", 0
                    ),
                    "latency_total": metadata.get("elapsed_ms", 0),
                    "data_quality": {
                        "parsed_ok": data_quality.get("parsed_ok", False),
                        "has_final_event": data_quality.get("has_final_event", False),
                        "has_metadata": data_quality.get("has_metadata", False),
                        "contract_warning_count": data_quality.get(
                            "contract_warning_count", 0
                        ),
                    },
                },
            }
        )

        failures = _flow_validation_failures(query_item)

        if failures:
            validation_failures.append(
                {
                    "case_id": query_item.get("case_id"),
                    "reasons": failures,
                }
            )

    weighted = _weighted_aggregates(
        weights,
        {
            "success_rate": success_flags,
            "false_success_rate": false_success_flags,
            "fallback_rate": fallback_flags,
            "loop_failures": loop_failure_flags,
            "tool_efficiency": tool_efficiency_scores,
            "tool_misuse": tool_misuse_scores,
            "reasoning_stability": reasoning_stability_scores,
            "iterations_count": iterations_values,
            "tool_calls_count": tool_calls_values,
            "reclassifications_count": reclass_values,
            "latency_total": latency_values,
        },
    )
    unweighted = {
        "success_rate": _avg(success_flags),
        "false_success_rate": _avg(false_success_flags),
        "fallback_rate": _avg(fallback_flags),
        "loop_failures": _avg(loop_failure_flags),
        "tool_efficiency": _avg(tool_efficiency_scores),
        "tool_misuse": _avg(tool_misuse_scores),
        "reasoning_stability": _avg(reasoning_stability_scores),
        "iterations_count": _avg(iterations_values),
        "tool_calls_count": _avg(tool_calls_values),
        "reclassifications_count": _avg(reclass_values),
        "latency_total": _avg(latency_values),
    }

    return {
        "run_id": run_payload.get("run_id"),
        "versions": manifest.get("versions", {}),
        "dataset_checksum": manifest.get("dataset_checksum"),
        "dataset_size": manifest.get("dataset_size", len(queries)),
        "evaluation_mode": "flow",
        "aggregated": {
            "weighted": weighted,
            "unweighted": unweighted,
            "error_classification": {},
        },
        "queries": query_reports,
        "flow_validation": {
            "valid": len(validation_failures) == 0,
            "failures": validation_failures,
        },
    }


def _evaluate_flow_query(query_item: Dict[str, Any]) -> Dict[str, Any]:
    primary = query_item.get("primary_repeat", {})
    stop_reason = str(primary.get("stop_reason", "unknown"))
    metadata = primary.get("metadata", {}) or {}
    data_quality = primary.get("data_quality", {}) or {}
    expected_tools = set(query_item.get("expected_tools", []))
    used_tools = primary.get("tools_used", [])

    iterations_count = int(metadata.get("iterations_count", 0) or 0)
    tool_calls_count = int(metadata.get("tool_calls_count", 0) or 0)

    valid_stop = stop_reason in FLOW_VALID_STOP_REASONS
    parsed_ok = bool(data_quality.get("parsed_ok", False))
    has_final = bool(data_quality.get("has_final_event", False))
    has_metadata = bool(data_quality.get("has_metadata", False))
    no_structural_error = (
        query_item.get("status", "completed") == "completed"
        and valid_stop
        and parsed_ok
        and has_final
        and has_metadata
        and iterations_count > 0
    )

    # In flow mode, expected tools drive structure quality, not semantic text quality.
    if expected_tools:
        overlap = len(expected_tools.intersection(set(used_tools)))
        tools_ok = overlap > 0
    else:
        tools_ok = True

    if query_item.get("query_type") == "multi-step":
        tools_ok = tools_ok and tool_calls_count > 0

    success = no_structural_error and tools_ok and stop_reason == FLOW_SUCCESS_REASON

    false_success = stop_reason == FLOW_SUCCESS_REASON and (
        not no_structural_error or not tools_ok
    )

    return {
        "success": success,
        "false_success": false_success,
        "valid_stop_reason": valid_stop,
        "has_structural_integrity": no_structural_error,
        "expected_tools_used": tools_ok,
    }


def _flow_validation_failures(query_item: Dict[str, Any]) -> List[str]:
    primary = query_item.get("primary_repeat", {})
    metadata = primary.get("metadata", {}) or {}
    iterations_count = int(metadata.get("iterations_count", 0) or 0)
    tool_calls_count = int(metadata.get("tool_calls_count", 0) or 0)

    failures: List[str] = []
    query_type = str(query_item.get("query_type", "simple"))

    if query_type != "simple" and iterations_count <= 0:
        failures.append("iterations_count_zero_non_trivial")

    if query_type == "multi-step" and tool_calls_count <= 0:
        failures.append("tool_calls_zero_multi_step")

    return failures


def _analyze_tool_efficiency(
    tools_used: List[str], expected_tools: List[str], stop_reason: str
) -> Dict[str, Any]:
    redundant_tools = _find_redundant_tools(tools_used)
    irrelevant_tools = [
        tool for tool in tools_used if expected_tools and tool not in expected_tools
    ]

    useful_count = 0
    total_tools = len(tools_used)
    if total_tools == 0:
        efficiency = 1.0 if stop_reason == FLOW_SUCCESS_REASON else 0.0
        return {
            "efficiency": efficiency,
            "tools_total": 0,
            "tools_useful": 0,
            "tools_redundant": [],
            "tools_irrelevant": [],
            "misuse_score": 0.0,
        }

    expected_set = set(expected_tools)
    for tool in tools_used:
        if expected_set:
            if tool in expected_set and tool not in redundant_tools:
                useful_count += 1
        elif tool not in redundant_tools:
            useful_count += 1

    efficiency = useful_count / total_tools
    misuse_score = (len(redundant_tools) + len(irrelevant_tools)) / total_tools

    return {
        "efficiency": round(efficiency, 4),
        "tools_total": total_tools,
        "tools_useful": useful_count,
        "tools_redundant": redundant_tools,
        "tools_irrelevant": irrelevant_tools,
        "misuse_score": round(misuse_score, 4),
    }


def _find_redundant_tools(tools_used: List[str]) -> List[str]:
    redundant: List[str] = []
    for idx in range(1, len(tools_used)):
        if tools_used[idx] == tools_used[idx - 1]:
            redundant.append(tools_used[idx])
    return redundant


def _compute_reasoning_stability(repeats: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not repeats:
        return {
            "stability_score": 0.0,
            "action_sequence_consistency": 0.0,
            "stop_reason_consistency": 0.0,
            "tool_set_consistency": 0.0,
        }

    action_counter = Counter(
        _signature_sequence(item.get("action_sequence", [])) for item in repeats
    )
    stop_counter = Counter(str(item.get("stop_reason", "unknown")) for item in repeats)
    tool_set_counter = Counter(
        tuple(sorted(set(item.get("tools_used", [])))) for item in repeats
    )

    total = len(repeats)
    action_consistency = _max_counter_ratio(action_counter, total)
    stop_consistency = _max_counter_ratio(stop_counter, total)
    tool_consistency = _max_counter_ratio(tool_set_counter, total)

    score = (action_consistency + stop_consistency + tool_consistency) / 3.0
    return {
        "stability_score": round(score, 4),
        "action_sequence_consistency": round(action_consistency, 4),
        "stop_reason_consistency": round(stop_consistency, 4),
        "tool_set_consistency": round(tool_consistency, 4),
        "repeats_count": total,
    }


def _max_counter_ratio(counter: Counter, total: int) -> float:
    if total <= 0 or not counter:
        return 0.0
    return max(counter.values()) / total


def _signature_sequence(values: List[Any]) -> Tuple[str, ...]:
    return tuple(str(value) for value in values)


def _weighted_aggregates(
    weights: List[float], values: Dict[str, List[float]]
) -> Dict[str, float]:
    output: Dict[str, float] = {}
    for metric_name, metric_values in values.items():
        output[metric_name] = _weighted_average(metric_values, weights)
    return output


def _weighted_average(values: List[float], weights: List[float]) -> float:
    if not values or len(values) != len(weights):
        return 0.0
    denominator = sum(weights)
    if denominator == 0:
        return 0.0
    numerator = sum(value * weight for value, weight in zip(values, weights))
    return round(numerator / denominator, 6)


def _avg(values: List[float] | List[int]) -> float:
    if not values:
        return 0.0
    return round(float(mean(values)), 6)
