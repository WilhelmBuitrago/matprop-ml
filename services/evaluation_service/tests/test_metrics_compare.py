from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from metrics import compare_runs


def _base_report() -> dict:
    return {
        "evaluation_mode": "flow",
        "versions": {
            "agent_version": "1.0.0",
            "policy_version": "1.0.0",
            "evaluator_version": "1.0.0",
            "tools_version": "1.0.0",
        },
        "dataset_checksum": "abc",
        "aggregated": {
            "weighted": {
                "success_rate": 0.9,
                "false_success_rate": 0.0,
                "loop_failures": 0.1,
                "latency_total": 1000,
                "tool_calls_count": 3,
            }
        },
        "statistical_reliability": {"status": "ready"},
    }


def test_compare_runs_blocks_missing_versions():
    current = _base_report()
    baseline = _base_report()
    current["versions"]["tools_version"] = ""
    result = compare_runs(current_report=current, baseline_report=baseline)
    assert result["status"] == "blocked"
    assert result["reason"] == "missing_versions"


def test_compare_runs_hard_fails_when_false_success_increases():
    current = _base_report()
    baseline = _base_report()
    current["aggregated"]["weighted"]["false_success_rate"] = 0.05
    result = compare_runs(current_report=current, baseline_report=baseline)
    assert result["status"] == "fail"


def test_compare_runs_blocks_mode_mismatch():
    current = _base_report()
    baseline = _base_report()
    current["evaluation_mode"] = "flow"
    baseline["evaluation_mode"] = "model"

    result = compare_runs(current_report=current, baseline_report=baseline)

    assert result["status"] == "blocked"
    assert result["reason"] == "evaluation_mode_mismatch"
