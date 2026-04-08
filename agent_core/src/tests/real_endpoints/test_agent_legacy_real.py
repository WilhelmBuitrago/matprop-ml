from __future__ import annotations

from typing import Any, Dict, List

import pytest


pytestmark = [pytest.mark.real_endpoints, pytest.mark.integration_docker]


def _extract_trace_tools(trace_payload: Dict[str, Any]) -> List[str]:
    return [
        str(call.get("tool_name", ""))
        for call in trace_payload.get("tool_calls", [])
        if isinstance(call, dict)
    ]


def _assert_mode_or_skip(metadata: Dict[str, Any], expected: str) -> None:
    observed = str(metadata.get("policy_mode", "")).strip().lower()
    if observed != expected:
        pytest.skip(
            f"Service running in mode={observed!r}, expected {expected!r} for this suite"
        )


@pytest.fixture
def legacy_flow_state() -> Dict[str, Any]:
    return {}


def test_legacy_simple_material_query(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="legacy",
        mode="legacy",
        case_name="legacy_simple_material_query",
    )

    request_obj = test_request_builder(
        query="Find material mp-149 and summarize key properties.",
        max_iterations=4,
        max_tool_calls=4,
    )
    response, latency_ms = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "legacy")

    assert parsed.id
    assert parsed.choices and parsed.choices[0].get("text")
    assert int(metadata.get("iterations_count", 0)) >= 1
    assert int(metadata.get("tool_calls_count", 0)) >= 1

    trace = capture_trace(parsed.id)
    if trace["path"]:
        tools = _extract_trace_tools(trace["payload"])
        assert "query_materials_database" in tools
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))

    report_extra(observed=f"latency_ms={latency_ms}", expected="HTTP 200 + tool usage")


def test_legacy_multi_step_flow(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    legacy_flow_state,
    report_extra,
):
    report_extra(
        suite="legacy",
        mode="legacy",
        case_name="legacy_multi_step_flow",
    )

    request_obj = test_request_builder(
        query=(
            "Compare candidate materials for semiconductors and include supporting "
            "scientific documents before giving a recommendation."
        ),
        max_iterations=8,
        max_tool_calls=8,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "legacy")

    assert int(metadata.get("iterations_count", 0)) >= 2
    assert int(metadata.get("tool_calls_count", 0)) >= 2

    trace = capture_trace(parsed.id)
    if trace["path"]:
        payload = trace["payload"]
        tools = _extract_trace_tools(payload)
        assert len(tools) >= 2
        assert len(set(tools)) >= 1
        legacy_flow_state["request_id"] = parsed.id
        legacy_flow_state["tools"] = tools
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))


def test_legacy_stall_detection(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="legacy",
        mode="legacy",
        case_name="legacy_stall_detection",
    )

    request_obj = test_request_builder(
        query="The material must satisfy strict constraints with band gap less than 1.5.",
        max_iterations=8,
        max_tool_calls=8,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "legacy")

    assert metadata.get("stop_reason") == "stall_detected"

    trace = capture_trace(parsed.id)
    if trace["path"]:
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))


def test_legacy_budget_exhaustion(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="legacy",
        mode="legacy",
        case_name="legacy_budget_exhaustion",
        expected="budget constrained stop",
    )

    request_obj = test_request_builder(
        query="Find, compare, validate and summarize all useful semiconductor options.",
        max_iterations=2,
        max_tool_calls=2,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "legacy")

    stop_reason = str(metadata.get("stop_reason", ""))
    assert stop_reason in {"max_iterations", "max_tool_calls", "budget_exhausted"}
    assert int(metadata.get("iterations_count", 0)) <= 2
    assert int(metadata.get("tool_calls_count", 0)) <= 2

    trace = capture_trace(parsed.id)
    if trace["path"]:
        report_extra(
            trace_ref=trace["path"], stop_reason=stop_reason, observed=stop_reason
        )


def test_legacy_streaming(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_sse_events,
    report_extra,
):
    report_extra(
        suite="legacy",
        mode="legacy",
        case_name="legacy_streaming",
    )

    request_obj = test_request_builder(
        query="Search papers for silicon and stream the response.",
        stream=True,
        max_iterations=4,
        max_tool_calls=4,
    )
    response, _ = real_agent_client(request_obj, stream=True)
    assert response.status_code == 200

    events = parse_sse_events(response)
    event_names = [event.get("event") for event in events]
    assert "start" in event_names
    assert "loop_done" in event_names
    assert "final" in event_names

    final_event = next(event for event in events if event.get("event") == "final")
    final_data = final_event.get("data") or {}
    payload = final_data.get("response") or {}
    metadata = payload.get("metadata") or {}
    _assert_mode_or_skip(metadata, "legacy")

    report_extra(observed=f"events={event_names}", expected="start,loop_done,final")
