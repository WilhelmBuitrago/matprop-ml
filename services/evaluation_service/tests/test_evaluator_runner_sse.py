from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from evaluator_runner import EvaluationMode
from evaluator_runner import EvaluationRunner


def _runner(tmp_path):
    return EvaluationRunner(storage_base_dir=tmp_path / "storage")


def _start_payload():
    return {
        "request_id": "req-1",
        "query": "find mp-149",
    }


def _loop_done_payload(stop_reason: str = "sufficient_evidence"):
    return {
        "request_id": "req-1",
        "stop_reason": stop_reason,
        "iterations": 1,
        "tool_calls": 1,
    }


def _final_v3_payload(with_metadata: bool = True, text: str = "ok"):
    metadata = {
        "iterations_count": 1,
        "tool_calls_count": 1,
        "reclassifications_count": 0,
        "elapsed_ms": 9,
        "stop_reason": "sufficient_evidence",
    }
    return {
        "request_id": "req-1",
        "response": {
            "choices": [{"text": text}],
            "metadata": metadata if with_metadata else {},
        },
    }


def _final_v2_payload(with_metadata: bool = True):
    metadata = {
        "iterations_count": 1,
        "tool_calls_count": 1,
        "reclassifications_count": 0,
        "elapsed_ms": 9,
    }
    return {
        "type": "final",
        "request_id": "req-1",
        "iteration": 1,
        "action": "FINALIZE_SUCCESS",
        "reason_code": "sufficient_answer",
        "tool_name": None,
        "validated_result": {
            "text": "ok",
            "metadata": metadata if with_metadata else {},
        },
        "partial_state": {"execution_status": "done"},
    }


def test_parse_sse_stream_tracks_decode_errors(tmp_path):
    runner = _runner(tmp_path)
    lines = [
        ":keepalive",
        "event: start",
        'data: {"request_id": "r", "query": "find mp-149"}',
        "",
        "event: final",
        "data: {not-json}",
        "",
    ]

    events, diagnostics = runner._parse_sse_stream(lines)

    assert len(events) == 2
    assert diagnostics["events_total"] == 2
    assert diagnostics["event_counts"]["start"] == 1
    assert diagnostics["event_counts"]["final"] == 1
    assert diagnostics["decode_error_count"] == 1
    assert diagnostics["decode_errors"][0]["event"] == "final"


def test_extract_repeat_payload_requires_final_event(tmp_path):
    runner = _runner(tmp_path)
    events = [{"event": "start", "payload": _start_payload()}]

    with pytest.raises(ValueError, match="Missing final event"):
        runner._extract_repeat_payload(events)


def test_extract_repeat_payload_requires_metadata(tmp_path):
    runner = _runner(tmp_path)
    events = [
        {"event": "start", "payload": _start_payload()},
        {"event": "loop_done", "payload": _loop_done_payload()},
        {"event": "final", "payload": _final_v3_payload(with_metadata=False)},
    ]

    parsed = runner._extract_repeat_payload(events)
    assert parsed["stop_reason"] == "sufficient_evidence"
    assert parsed["metadata"]["iterations_count"] == 1
    assert parsed["metadata"]["tool_calls_count"] == 1


def test_extract_repeat_payload_returns_data_quality_flags(tmp_path):
    runner = _runner(tmp_path)
    mismatched_start = _start_payload()
    mismatched_start["type"] = "not_start"
    events = [
        {"event": "start", "payload": mismatched_start},
        {"event": "loop_done", "payload": _loop_done_payload()},
        {"event": "final", "payload": _final_v3_payload(with_metadata=True)},
    ]

    parsed = runner._extract_repeat_payload(events)

    assert parsed["stop_reason"] == "sufficient_evidence"
    assert parsed["response_text"] == "ok"
    assert parsed["metadata"]["iterations_count"] == 1
    assert parsed["data_quality"]["parsed_ok"] is True
    assert parsed["data_quality"]["has_final_event"] is True
    assert parsed["data_quality"]["has_metadata"] is True
    assert parsed["data_quality"]["contract_warning_count"] >= 1


def test_extract_repeat_payload_allows_empty_text_in_flow_only(tmp_path):
    runner = _runner(tmp_path)
    final_payload = _final_v3_payload(with_metadata=True, text="")
    events = [
        {"event": "start", "payload": _start_payload()},
        {"event": "loop_done", "payload": _loop_done_payload()},
        {"event": "final", "payload": final_payload},
    ]

    flow_parsed = runner._extract_repeat_payload(events, EvaluationMode.FLOW)
    assert flow_parsed["response_text"] == ""

    with pytest.raises(ValueError, match="response text"):
        runner._extract_repeat_payload(events, EvaluationMode.MODEL)


def test_extract_repeat_payload_accepts_legacy_v2_shape(tmp_path):
    runner = _runner(tmp_path)
    events = [
        {
            "event": "decision",
            "payload": {
                "type": "decision",
                "request_id": "req-1",
                "action": "CALL_TOOL",
                "tool_name": "search_materials",
            },
        },
        {"event": "final", "payload": _final_v2_payload(with_metadata=True)},
    ]

    parsed = runner._extract_repeat_payload(events)

    assert parsed["stop_reason"] == "sufficient_answer"
    assert parsed["response_text"] == "ok"
    assert parsed["metadata"]["iterations_count"] == 1
