from __future__ import annotations

from typing import Any, Dict, List

import pytest


pytestmark = [pytest.mark.real_endpoints, pytest.mark.integration_docker]


def _extract_trace_tools(trace_payload: Dict[str, Any]) -> List[str]:
    old = [
        str(call.get("tool_name", ""))
        for call in trace_payload.get("tool_calls", [])
        if isinstance(call, dict)
    ]
    if old:
        return old

    tools: List[str] = []
    for row in trace_payload.get("trace", []):
        if not isinstance(row, dict):
            continue
        if str(row.get("event", "")).strip() != "tool_start":
            continue
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool", "")).strip()
        if tool:
            tools.append(tool)
    return tools


def _assert_mode_or_skip(metadata: Dict[str, Any], expected: str) -> None:
    observed = str(metadata.get("policy_mode", "")).strip().lower()
    if observed != expected:
        pytest.skip(
            f"Service running in mode={observed!r}, expected {expected!r} for this suite"
        )


@pytest.fixture
def planned_flow_state() -> Dict[str, Any]:
    return {}


def test_planned_simple_material_query(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_simple_material_query",
    )

    request_obj = test_request_builder(
        query="Find material mp-149 and summarize key properties.",
        max_iterations=4,
        max_tool_calls=4,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "planned")

    assert parsed.id
    assert parsed.choices and parsed.choices[0].get("text")
    assert int(metadata.get("iterations_count", 0)) >= 1

    trace = capture_trace(parsed.id)
    if trace["path"]:
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))


def test_planned_multi_step_flow(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    planned_flow_state,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_multi_step_flow",
    )

    request_obj = test_request_builder(
        query=(
            "Plan a multi-step approach to compare semiconductors and include "
            "scientific evidence before recommending one."
        ),
        max_iterations=8,
        max_tool_calls=8,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "planned")

    assert int(metadata.get("tool_calls_count", 0)) >= 1

    trace = capture_trace(parsed.id)
    if trace["path"]:
        payload = trace["payload"]
        tools = _extract_trace_tools(payload)
        planned_flow_state["request_id"] = parsed.id
        planned_flow_state["tools"] = tools
        assert len(tools) >= 1
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))


def test_planned_stall_detection(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_stall_detection",
    )

    request_obj = test_request_builder(
        query="The material must satisfy strict constraints with band gap less than 1.5.",
        max_iterations=8,
        max_tool_calls=8,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "planned")

    assert metadata.get("stop_reason") in {
        "sufficient_evidence",
        "plan_exhausted",
        "budget_exhausted",
    }

    trace = capture_trace(parsed.id)
    if trace["path"]:
        report_extra(trace_ref=trace["path"], stop_reason=metadata.get("stop_reason"))


def test_planned_budget_exhaustion(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_budget_exhaustion",
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
    _assert_mode_or_skip(metadata, "planned")

    stop_reason = str(metadata.get("stop_reason", ""))
    assert stop_reason in {
        "max_iterations",
        "max_tool_calls",
        "budget_exhausted",
    }
    assert int(metadata.get("iterations_count", 0)) <= 2

    trace = capture_trace(parsed.id)
    if trace["path"]:
        report_extra(
            trace_ref=trace["path"], stop_reason=stop_reason, observed=stop_reason
        )


def test_planned_streaming(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_sse_events,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_streaming",
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
    assert "final" in event_names
    assert any(name in {"tool_start", "stop"} for name in event_names)

    final_event = next(event for event in events if event.get("event") == "final")
    final_data = final_event.get("data") or {}
    payload = final_data.get("response") or {}
    metadata = payload.get("metadata") or {}
    _assert_mode_or_skip(metadata, "planned")

    report_extra(observed=f"events={event_names}", expected="start,...,final")


def test_planned_fallback_to_legacy_when_planning_fails(
    require_real_services,
    real_agent_client,
    test_request_builder,
    parse_completion_response,
    capture_trace,
    report_extra,
):
    report_extra(
        suite="planned",
        mode="planned",
        case_name="planned_fallback_to_legacy",
        expected="planner failure triggers legacy fallback",
    )

    request_obj = test_request_builder(
        query=(
            "x " * 1200
            + "force planner stress and still produce a stable answer with tools"
        ).strip(),
        max_iterations=5,
        max_tool_calls=5,
    )
    response, _ = real_agent_client(request_obj)
    parsed = parse_completion_response(response)

    metadata = parsed.metadata or {}
    _assert_mode_or_skip(metadata, "planned")

    fallback_reason = str(metadata.get("fallback_reason", "")).strip()
    if not fallback_reason:
        pytest.skip("Fallback scenario not observed in this environment")

    assert metadata.get("fallback_engine") == "legacy"
    assert parsed.choices and parsed.choices[0].get("text")
    report_extra(observed=f"fallback_reason={fallback_reason}")
