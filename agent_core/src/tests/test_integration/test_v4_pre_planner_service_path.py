from __future__ import annotations

from api.v4.pre_planner_decision import PrePlannerDecision, PrePlannerRoute
from api.v4.scheme import CompletionRequestV4


def _direct_route() -> PrePlannerRoute:
    return PrePlannerRoute(
        use_tools=False,
        route="direct_llm",
        decision=PrePlannerDecision(
            calling_tools=False,
            confidence=0.95,
            reasoning="Can answer directly from base model knowledge.",
        ),
    )


def _full_route() -> PrePlannerRoute:
    return PrePlannerRoute(
        use_tools=True,
        route="full_pipeline",
        decision=PrePlannerDecision(
            calling_tools=True,
            confidence=0.9,
            reasoning="Tooling required.",
        ),
    )


def test_chat_direct_llm_path_bypasses_pipeline(make_service, monkeypatch):
    service = make_service()

    monkeypatch.setattr(service.runtime.pre_planner, "evaluate", lambda _q: _direct_route())

    calls: dict[str, int] = {"entry": 0, "planner": 0, "loop": 0, "direct": 0}

    def _entry_should_not_run(*_args, **_kwargs):
        calls["entry"] += 1
        raise AssertionError("entry_policy.select_tools must be bypassed on direct_llm")

    def _planner_should_not_run(*_args, **_kwargs):
        calls["planner"] += 1
        raise AssertionError("planner.build_plan must be bypassed on direct_llm")

    async def _loop_should_not_run(*_args, **_kwargs):
        calls["loop"] += 1
        raise AssertionError("run_loop must be bypassed on direct_llm")

    def _direct_call(*, query: str, temperature: float, max_tokens: int):
        calls["direct"] += 1
        assert query
        assert max_tokens > 0
        return "Direct fast-path answer", None

    monkeypatch.setattr(service.runtime.entry_policy, "select_tools", _entry_should_not_run)
    monkeypatch.setattr("api.v4.service.DeepSeekOneShotPlanner.build_plan", _planner_should_not_run)
    monkeypatch.setattr("api.v4.service.run_loop", _loop_should_not_run)
    monkeypatch.setattr(service, "_direct_llm_call", _direct_call)

    response = service.chat(
        CompletionRequestV4(
            query="What is the role of defects in semiconductors?",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.choices[0]["text"] == "Direct fast-path answer"
    assert response.metadata["stop_reason_canonical"] == "direct_llm"
    assert response.metadata["iterations_count"] == 0
    assert response.metadata["tool_calls_count"] == 0
    assert calls == {"entry": 0, "planner": 0, "loop": 0, "direct": 1}


def test_stream_direct_llm_path_emits_final(make_service, monkeypatch):
    service = make_service()

    monkeypatch.setattr(service.runtime.pre_planner, "evaluate", lambda _q: _direct_route())
    monkeypatch.setattr(
        service,
        "_direct_llm_call",
        lambda **_kwargs: ("Direct stream fast-path answer", None),
    )

    events = list(
        service.stream_chat_events(
            CompletionRequestV4(
                query="Explain grain boundaries in materials.",
                stream=True,
            )
        )
    )

    assert any(e.startswith("event: start") for e in events)
    assert any(e.startswith("event: final") for e in events)


def test_chat_full_pipeline_still_works(make_service, monkeypatch):
    service = make_service()

    monkeypatch.setattr(service.runtime.pre_planner, "evaluate", lambda _q: _full_route())

    response = service.chat(
        CompletionRequestV4(
            query="find material mp-149 and summarize",
            max_iterations=4,
            max_tool_calls=4,
        )
    )

    assert response.metadata["stop_reason_canonical"] in {
        "completed",
        "plan_exhausted",
        "max_iterations",
        "max_tool_calls",
    }
    assert isinstance(response.choices[0]["text"], str)
