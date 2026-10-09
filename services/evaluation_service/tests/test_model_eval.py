from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from metrics import compute_metrics


def _base_run_payload() -> dict:
    return {
        "run_id": "run-model-1",
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
                "query": "find mp-149",
                "difficulty": "easy",
                "weight": 1.0,
                "query_type": "simple",
                "expected_outcome_type": "sufficient",
                "expected_behavior": "return material properties",
                "expected_tools": ["search_materials"],
                "status": "completed",
                "primary_repeat": {
                    "stop_reason": "sufficient_evidence",
                    "response_text": "return material properties",
                    "tools_used": ["search_materials"],
                    "metadata": {
                        "iterations_count": 1,
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


def test_model_eval_fails_when_response_text_is_missing():
    run_payload = _base_run_payload()
    run_payload["queries"][0]["primary_repeat"]["response_text"] = ""

    metrics = compute_metrics(run_payload, evaluation_mode="model")

    assert metrics["evaluation_mode"] == "model"
    assert metrics["aggregated"]["weighted"]["success_rate"] == 0.0
    assert metrics["queries"][0]["success"] is False


def test_hybrid_mode_flow_gates_model_success():
    run_payload = _base_run_payload()

    # Force flow to fail structurally while keeping model text valid.
    run_payload["queries"][0]["primary_repeat"]["metadata"]["iterations_count"] = 0

    metrics = compute_metrics(run_payload, evaluation_mode="hybrid")

    assert metrics["evaluation_mode"] == "hybrid"
    assert metrics["queries"][0]["flow_success"] is False
    assert metrics["queries"][0]["model_success"] is True
    assert metrics["queries"][0]["success"] is False
