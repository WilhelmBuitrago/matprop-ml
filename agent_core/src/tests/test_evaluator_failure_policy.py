from api.v4.failure_policy import handle_evaluator_failure
from api.v4.history_item import HistoryItem


def test_failure_policy_uses_context_when_tool_results_exist():
    history = [
        HistoryItem(role="user", type="query", content="find Si"),
        HistoryItem(role="tool", type="tool_result", content='{"ok": true}'),
    ]

    assert handle_evaluator_failure(history) == "final_with_context"


def test_failure_policy_uses_query_only_without_tool_results():
    history = [
        HistoryItem(role="user", type="query", content="find Si"),
        HistoryItem(role="assistant", type="plan", content="{}"),
    ]

    assert handle_evaluator_failure(history) == "final_without_context"
