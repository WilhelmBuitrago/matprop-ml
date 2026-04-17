from api.v4.resilience_policy import ResiliencePolicy


def test_level2_planner_failure_property_query_selects_db_tool():
    policy = ResiliencePolicy()

    decision = policy.level2_for_planner_failure(
        query="need band gap and density for silicon",
        reason="planner_failed",
    )

    assert decision.level == 2
    assert decision.action == "force_single_tool_plan"
    assert decision.details["query_type"] == "property_query"
    assert decision.details["selected_tool"] == "query_materials_database"
    assert decision.details["deterministic"] is True


def test_level2_planner_failure_literature_selects_rag_pipeline():
    policy = ResiliencePolicy()

    decision = policy.level2_for_planner_failure(
        query="find literature and doi references for perovskites",
        reason="invalid_plan",
    )

    assert decision.level == 2
    assert decision.action == "force_single_tool_plan"
    assert decision.details["query_type"] == "literature"
    assert decision.details["selected_tool"] == "document_rag"
    assert decision.details["deterministic"] is True


def test_level3_requires_multiple_failures_or_invalid_results():
    policy = ResiliencePolicy()

    none_decision = policy.level3_for_tool_failures(
        failed_tools=1,
        invalid_or_empty_results=1,
    )
    assert none_decision is None

    decision = policy.level3_for_tool_failures(
        failed_tools=2,
        invalid_or_empty_results=0,
    )
    assert decision is not None
    assert decision.level == 3
    assert decision.action == "final_model_direct_fallback"
    assert decision.details["deterministic"] is True
    assert decision.details["model"] == "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"


def test_level4_returns_explicit_limitation_action():
    policy = ResiliencePolicy()

    decision = policy.level4_for_final_model_failure("connection reset")

    assert decision.level == 4
    assert decision.action == "explicit_limitation_response"
    assert decision.reason == "final_model_failed"
    assert decision.details["error"] == "connection reset"
    assert decision.details["deterministic"] is True
