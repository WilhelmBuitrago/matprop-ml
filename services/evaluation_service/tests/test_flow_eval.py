from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from metrics import compute_metrics


def _base_run_payload() -> dict:
    return {
        "run_id": "run-flow-1",
        "manifest": {
            "dataset_checksum": "checksum-1",
            "dataset_size": 1,
            "versions": {
                "agent_version": "1.0.0",
                "policy_version": "1.0.0",
                "evaluator_version": "1.0.0",
                "tools_version": "1.0.0",
            },
        },
        "queries": [
            {
                "case_id": "case-1",
                "query": "material multi-step",
                "difficulty": "medium",
                "weight": 1.0,
                "query_type": "multi-step",
                "expected_tools": ["search_materials"],
                "status": "completed",
                "primary_repeat": {
                    "stop_reason": "sufficient_evidence",
                    "response_text": "",
                    "tools_used": ["search_materials"],
                    "metadata": {
                        "iterations_count": 2,
                        "tool_calls_count": 1,
                        "reclassifications_count": 0,
                        "elapsed_ms": 100,
                    },
                    "data_quality": {
                        "parsed_ok": True,
                        "has_final_event": True,
                        "has_metadata": True,
                        "contract_warning_count": 0,
                    },
                },
                "repeats": [
                    {
                        "action_sequence": ["CALL_TOOL", "FINALIZE_SUCCESS"],
                        "stop_reason": "sufficient_evidence",
                        "tools_used": ["search_materials"],
                    }
                ],
            }
        ],
    }


def test_flow_eval_ignores_response_text_quality():
    run_payload = _base_run_payload()
    metrics = compute_metrics(run_payload, evaluation_mode="flow")

    assert metrics["evaluation_mode"] == "flow"
    assert metrics["aggregated"]["weighted"]["success_rate"] == 1.0
    assert metrics["queries"][0]["success"] is True


def test_flow_run_invalid_when_non_trivial_has_zero_iterations():
    run_payload = _base_run_payload()
    run_payload["queries"][0]["primary_repeat"]["metadata"]["iterations_count"] = 0

    metrics = compute_metrics(run_payload, evaluation_mode="flow")

    assert metrics["flow_validation"]["valid"] is False
    assert (
        metrics["flow_validation"]["failures"][0]["reasons"][0]
        == "iterations_count_zero_non_trivial"
    )
