from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Tuple

from flow_evaluator import compute_flow_metrics


REQUIRED_VERSION_KEYS = [
    "agent_version",
    "policy_version",
    "evaluator_version",
    "tools_version",
]

FAILURE_STOP_REASONS = {
    "budget_exhausted",
    "no_valid_tools_available",
    "stall_detected",
    "tool_input_validation_failed",
    "tool_output_validation_failed",
    # Legacy compatibility
    "controlled_failure",
    "max_iterations",
    "max_tool_calls",
    "max_wall_time_ms",
    "max_context_tokens",
    "invalid_response",
    "timeout",
}

FALLBACK_STOP_REASONS = {
    "budget_exhausted",
    "no_valid_tools_available",
    "stall_detected",
    # Legacy compatibility
    "controlled_failure",
}

SUCCESS_STOP_REASON = "sufficient_evidence"


def compute_metrics(
    run_payload: Dict[str, Any],
    evaluation_mode: str = "flow",
) -> Dict[str, Any]:
    mode = str(evaluation_mode or "flow").lower()
    if mode == "flow":
        return compute_flow_metrics(run_payload)

    if mode == "model":
        model_payload = _compute_model_metrics(run_payload)
        model_payload["evaluation_mode"] = "model"
        return model_payload

    if mode == "hybrid":
        flow_payload = compute_flow_metrics(run_payload)
        model_payload = _compute_model_metrics(run_payload)
        return _compute_hybrid_metrics(run_payload, flow_payload, model_payload)

    raise ValueError(f"Unsupported evaluation_mode: {evaluation_mode}")


def _compute_model_metrics(run_payload: Dict[str, Any]) -> Dict[str, Any]:
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
    parsed_ok_flags: List[int] = []
    has_final_flags: List[int] = []
    has_metadata_flags: List[int] = []

    error_class_counts = Counter()

    for query_item in queries:
        primary = query_item.get("primary_repeat", {})
        repeats = query_item.get("repeats", [])
        stop_reason = str(primary.get("stop_reason", "unknown"))
        metadata = primary.get("metadata", {}) or {}
        data_quality = primary.get("data_quality", {}) or {}

        expected_outcome = _safe_get(query_item, "expected_outcome_type")
        evaluator = _evaluate_query_outcome(query_item)

        success = _is_success(expected_outcome, stop_reason, evaluator)
        false_success = _is_false_success(expected_outcome, stop_reason, evaluator)

        tool_analysis = _analyze_tool_efficiency(query_item)
        stability = _compute_reasoning_stability(repeats)

        weight = float(query_item.get("weight", 1.0))
        weights.append(weight)
        success_flags.append(1 if success else 0)
        false_success_flags.append(1 if false_success else 0)
        fallback_flags.append(1 if stop_reason in FALLBACK_STOP_REASONS else 0)
        loop_failure_flags.append(1 if stop_reason in FAILURE_STOP_REASONS else 0)
        tool_efficiency_scores.append(tool_analysis["efficiency"])
        reasoning_stability_scores.append(stability["stability_score"])
        tool_misuse_scores.append(tool_analysis["misuse_score"])

        iterations_values.append(float(metadata.get("iterations_count", 0)))
        tool_calls_values.append(float(metadata.get("tool_calls_count", 0)))
        reclass_values.append(float(metadata.get("reclassifications_count", 0)))
        latency_values.append(float(metadata.get("elapsed_ms", 0)))
        parsed_ok_flags.append(1 if data_quality.get("parsed_ok", False) else 0)
        has_final_flags.append(1 if data_quality.get("has_final_event", False) else 0)
        has_metadata_flags.append(1 if data_quality.get("has_metadata", False) else 0)

        error_label = _classify_query_error(query_item)
        if error_label:
            error_class_counts[error_label] += 1

        query_reports.append(
            {
                "case_id": query_item.get("case_id"),
                "query": query_item.get("query"),
                "difficulty": query_item.get("difficulty"),
                "weight": weight,
                "expected_outcome_type": expected_outcome,
                "stop_reason": stop_reason,
                "evaluator": evaluator,
                "success": success,
                "false_success": false_success,
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
                "error_class": error_label,
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
            "reasoning_stability": reasoning_stability_scores,
            "tool_misuse": tool_misuse_scores,
            "iterations_count": iterations_values,
            "tool_calls_count": tool_calls_values,
            "reclassifications_count": reclass_values,
            "latency_total": latency_values,
            "parsed_ok_rate": parsed_ok_flags,
            "has_final_event_rate": has_final_flags,
            "has_metadata_rate": has_metadata_flags,
        },
    )

    unweighted = {
        "success_rate": _avg(success_flags),
        "false_success_rate": _avg(false_success_flags),
        "fallback_rate": _avg(fallback_flags),
        "loop_failures": _avg(loop_failure_flags),
        "tool_efficiency": _avg(tool_efficiency_scores),
        "reasoning_stability": _avg(reasoning_stability_scores),
        "tool_misuse": _avg(tool_misuse_scores),
        "iterations_count": _avg(iterations_values),
        "tool_calls_count": _avg(tool_calls_values),
        "reclassifications_count": _avg(reclass_values),
        "latency_total": _avg(latency_values),
        "parsed_ok_rate": _avg(parsed_ok_flags),
        "has_final_event_rate": _avg(has_final_flags),
        "has_metadata_rate": _avg(has_metadata_flags),
    }

    return {
        "run_id": run_payload.get("run_id"),
        "versions": manifest.get("versions", {}),
        "dataset_checksum": manifest.get("dataset_checksum"),
        "dataset_size": manifest.get("dataset_size", len(queries)),
        "evaluation_mode": "model",
        "aggregated": {
            "weighted": weighted,
            "unweighted": unweighted,
            "error_classification": dict(error_class_counts),
        },
        "queries": query_reports,
    }


def _compute_hybrid_metrics(
    run_payload: Dict[str, Any],
    flow_payload: Dict[str, Any],
    model_payload: Dict[str, Any],
) -> Dict[str, Any]:
    flow_by_case = {
        item.get("case_id"): item for item in flow_payload.get("queries", [])
    }
    model_by_case = {
        item.get("case_id"): item for item in model_payload.get("queries", [])
    }

    combined_queries: List[Dict[str, Any]] = []
    weights: List[float] = []
    hybrid_success_flags: List[int] = []
    hybrid_false_success_flags: List[int] = []

    for query_item in run_payload.get("queries", []):
        case_id = query_item.get("case_id")
        flow_query = flow_by_case.get(case_id, {})
        model_query = model_by_case.get(case_id, {})

        flow_success = bool(flow_query.get("success", False))
        model_success = bool(model_query.get("success", False))
        hybrid_success = flow_success and model_success

        flow_false_success = bool(flow_query.get("false_success", False))
        model_false_success = bool(model_query.get("false_success", False))
        hybrid_false_success = flow_false_success or model_false_success

        weight = float(query_item.get("weight", 1.0))
        weights.append(weight)
        hybrid_success_flags.append(1 if hybrid_success else 0)
        hybrid_false_success_flags.append(1 if hybrid_false_success else 0)

        combined_queries.append(
            {
                "case_id": case_id,
                "query": query_item.get("query"),
                "difficulty": query_item.get("difficulty"),
                "weight": weight,
                "flow_success": flow_success,
                "model_success": model_success,
                "success": hybrid_success,
                "false_success": hybrid_false_success,
                "flow": flow_query,
                "model": model_query,
            }
        )

    weighted = {
        "success_rate": _weighted_average(hybrid_success_flags, weights),
        "false_success_rate": _weighted_average(hybrid_false_success_flags, weights),
        "flow_success_rate": flow_payload.get("aggregated", {})
        .get("weighted", {})
        .get("success_rate", 0.0),
        "model_success_rate": model_payload.get("aggregated", {})
        .get("weighted", {})
        .get("success_rate", 0.0),
    }
    unweighted = {
        "success_rate": _avg(hybrid_success_flags),
        "false_success_rate": _avg(hybrid_false_success_flags),
        "flow_success_rate": flow_payload.get("aggregated", {})
        .get("unweighted", {})
        .get("success_rate", 0.0),
        "model_success_rate": model_payload.get("aggregated", {})
        .get("unweighted", {})
        .get("success_rate", 0.0),
    }

    return {
        "run_id": run_payload.get("run_id"),
        "versions": run_payload.get("manifest", {}).get("versions", {}),
        "dataset_checksum": run_payload.get("manifest", {}).get("dataset_checksum"),
        "dataset_size": run_payload.get("manifest", {}).get(
            "dataset_size", len(combined_queries)
        ),
        "evaluation_mode": "hybrid",
        "hybrid_gate": {
            "policy": "flow_gates_model",
            "flow_valid": flow_payload.get("flow_validation", {}).get("valid", True),
        },
        "aggregated": {
            "weighted": weighted,
            "unweighted": unweighted,
            "error_classification": model_payload.get("aggregated", {}).get(
                "error_classification", {}
            ),
        },
        "queries": combined_queries,
        "flow_metrics": flow_payload,
        "model_metrics": model_payload,
    }


def assess_statistical_reliability(
    run_payload: Dict[str, Any],
    min_dataset_size: int = 10,
    min_cases_per_difficulty: int = 1,
    min_repeats: int = 3,
) -> Dict[str, Any]:
    queries = run_payload.get("queries", [])
    manifest = run_payload.get("manifest", {})

    issues: List[str] = []
    warnings: List[str] = []

    if len(queries) < min_dataset_size:
        issues.append(
            f"Dataset too small for comparison: {len(queries)} < {min_dataset_size}"
        )

    difficulty_counts = Counter(item.get("difficulty", "unknown") for item in queries)
    for difficulty in ["easy", "medium", "hard"]:
        count = difficulty_counts.get(difficulty, 0)
        if count < min_cases_per_difficulty:
            issues.append(
                f"Insufficient difficulty coverage for '{difficulty}': {count}"
            )

    for query_item in queries:
        repeats = query_item.get("repeats", [])
        if len(repeats) < min_repeats:
            issues.append(
                f"Case {query_item.get('case_id')} has repeats {len(repeats)} < {min_repeats}"
            )

    status = "ready"
    if issues:
        status = "blocked"
    elif len(queries) < (min_dataset_size * 2):
        status = "warning"
        warnings.append("Dataset size is borderline for robust trend analysis")

    return {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "dataset_size": len(queries),
        "repeat_count_expected": manifest.get("reproducibility", {}).get(
            "repeat_count", min_repeats
        ),
    }


def compare_runs(
    current_report: Dict[str, Any],
    baseline_report: Dict[str, Any],
    thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    thresholds = thresholds or {
        "success_rate": -0.02,
        "false_success_rate": 0.01,
        "loop_failures": 0.02,
        "latency_total": 0.10,
        "tool_calls_count": 0.15,
    }

    current_versions = current_report.get("versions", {})
    baseline_versions = baseline_report.get("versions", {})
    current_mode = str(current_report.get("evaluation_mode", "flow"))
    baseline_mode = str(baseline_report.get("evaluation_mode", "flow"))
    if current_mode != baseline_mode:
        return {
            "status": "blocked",
            "reason": "evaluation_mode_mismatch",
            "current_mode": current_mode,
            "baseline_mode": baseline_mode,
        }

    missing_current = [
        key for key in REQUIRED_VERSION_KEYS if not current_versions.get(key)
    ]
    missing_baseline = [
        key for key in REQUIRED_VERSION_KEYS if not baseline_versions.get(key)
    ]
    if missing_current or missing_baseline:
        return {
            "status": "blocked",
            "reason": "missing_versions",
            "missing_current": missing_current,
            "missing_baseline": missing_baseline,
        }

    current_reliability = current_report.get("statistical_reliability", {})
    baseline_reliability = baseline_report.get("statistical_reliability", {})
    if current_reliability.get("status") == "blocked":
        return {
            "status": "blocked",
            "reason": "current_statistical_reliability_blocked",
            "details": current_reliability,
        }
    if baseline_reliability.get("status") == "blocked":
        return {
            "status": "blocked",
            "reason": "baseline_statistical_reliability_blocked",
            "details": baseline_reliability,
        }

    current_metrics = current_report.get("aggregated", {}).get("weighted", {})
    baseline_metrics = baseline_report.get("aggregated", {}).get("weighted", {})

    degradations: List[Dict[str, Any]] = []
    improved: List[Dict[str, Any]] = []

    for metric_name, threshold in thresholds.items():
        current_value = float(current_metrics.get(metric_name, 0.0))
        baseline_value = float(baseline_metrics.get(metric_name, 0.0))
        delta = current_value - baseline_value

        is_bad_direction = False
        if metric_name == "success_rate":
            is_bad_direction = delta < threshold
        elif metric_name == "false_success_rate":
            is_bad_direction = delta > threshold
        else:
            is_bad_direction = delta > threshold

        result_payload = {
            "metric": metric_name,
            "current": current_value,
            "baseline": baseline_value,
            "delta": delta,
            "threshold": threshold,
        }
        if is_bad_direction:
            degradations.append(result_payload)
        else:
            improved.append(result_payload)

    # Hard fail rule.
    false_success_delta = float(current_metrics.get("false_success_rate", 0.0)) - float(
        baseline_metrics.get("false_success_rate", 0.0)
    )

    status = "pass"
    if false_success_delta > 0:
        status = "fail"
        degradations.append(
            {
                "metric": "false_success_rate",
                "delta": false_success_delta,
                "reason": "hard_fail_rule",
            }
        )
    elif degradations:
        status = "fail"
    elif (
        current_reliability.get("status") == "warning"
        or baseline_reliability.get("status") == "warning"
    ):
        status = "warn"

    return {
        "status": status,
        "dataset_match": current_report.get("dataset_checksum")
        == baseline_report.get("dataset_checksum"),
        "degradations": degradations,
        "improved_or_within_threshold": improved,
    }


def _evaluate_query_outcome(query_item: Dict[str, Any]) -> Dict[str, Any]:
    primary = query_item.get("primary_repeat", {})
    text = str(primary.get("response_text", "")).strip()
    tools_used = primary.get("tools_used", [])
    expected_behavior = str(query_item.get("expected_behavior", "")).strip()

    coverage_score = _keyword_overlap_ratio(expected_behavior, text)
    coherence_score = 1.0 if text else 0.0
    if expected_behavior and not text:
        coherence_score = 0.0
    elif expected_behavior and coverage_score < 0.15:
        coherence_score = 0.25

    tool_signal = 1.0
    expected_tools = set(query_item.get("expected_tools", []))
    if expected_tools:
        overlap = len(expected_tools.intersection(set(tools_used)))
        tool_signal = overlap / len(expected_tools)

    aggregate_score = (coverage_score + coherence_score + tool_signal) / 3.0
    if aggregate_score >= 0.66:
        klass = "SUFFICIENT"
    elif aggregate_score >= 0.33:
        klass = "INSUFFICIENT"
    else:
        klass = "TERMINAL_FAILURE"

    return {
        "klass": klass,
        "coverage_score": round(coverage_score, 4),
        "coherence_score": round(coherence_score, 4),
        "tool_signal": round(tool_signal, 4),
        "aggregate_score": round(aggregate_score, 4),
    }


def _is_success(
    expected_outcome: str,
    stop_reason: str,
    evaluator: Dict[str, Any],
) -> bool:
    klass = evaluator.get("klass")
    if expected_outcome == "sufficient":
        return stop_reason == SUCCESS_STOP_REASON and klass == "SUFFICIENT"
    if expected_outcome == "failure":
        return stop_reason in FAILURE_STOP_REASONS and klass != "SUFFICIENT"
    if expected_outcome == "partial":
        return klass == "INSUFFICIENT" and stop_reason not in {
            "invalid_response",
            "timeout",
        }
    return False


def _is_false_success(
    expected_outcome: str,
    stop_reason: str,
    evaluator: Dict[str, Any],
) -> bool:
    klass = evaluator.get("klass")
    if stop_reason == SUCCESS_STOP_REASON and klass != "SUFFICIENT":
        return True
    if stop_reason == SUCCESS_STOP_REASON and expected_outcome != "sufficient":
        return True
    return False


def _analyze_tool_efficiency(query_item: Dict[str, Any]) -> Dict[str, Any]:
    tools_used = query_item.get("primary_repeat", {}).get("tools_used", [])
    expected_tools = query_item.get("expected_tools", [])

    redundant_tools = _find_redundant_tools(tools_used)
    irrelevant_tools = [
        tool for tool in tools_used if expected_tools and tool not in expected_tools
    ]

    useful_count = 0
    total_tools = len(tools_used)
    if total_tools == 0:
        stop_reason = query_item.get("primary_repeat", {}).get("stop_reason")
        efficiency = 1.0 if stop_reason == SUCCESS_STOP_REASON else 0.0
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
    if not values:
        return 0.0
    if len(values) != len(weights):
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


def _keyword_overlap_ratio(expected_behavior: str, response_text: str) -> float:
    expected_tokens = _tokenize(expected_behavior)
    response_tokens = _tokenize(response_text)
    if not expected_tokens:
        return 0.0
    overlap = len(expected_tokens.intersection(response_tokens))
    return overlap / max(1, len(expected_tokens))


def _tokenize(text: str) -> set[str]:
    result = set()
    for token in text.lower().replace("\n", " ").split(" "):
        normalized = "".join(ch for ch in token if ch.isalnum())
        if len(normalized) >= 3:
            result.add(normalized)
    return result


def _safe_get(query_item: Dict[str, Any], key: str) -> str:
    if key in query_item:
        return str(query_item.get(key))
    return str(query_item.get("dataset_case", {}).get(key, ""))


def _classify_query_error(query_item: Dict[str, Any]) -> str | None:
    if query_item.get("status") == "completed":
        return None

    label_counter = Counter()
    for repeat in query_item.get("repeats", []):
        label = repeat.get("error_label")
        if label:
            label_counter[label] += 1

    if not label_counter:
        return "invalid_response"
    return label_counter.most_common(1)[0][0]
