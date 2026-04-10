from api.v4.history_item import HistoryItem
from api.v4.truncation import truncate_history


def test_truncation_keeps_recent_items_within_budget():
    history = [
        HistoryItem(role="user", type="query", content="q" * 20),
        HistoryItem(role="assistant", type="plan", content="p" * 40),
        HistoryItem(role="tool", type="tool_result", content="r" * 60),
    ]

    truncated = truncate_history(history, max_tokens=20)

    assert truncated
    assert truncated[-1].type == "tool_result"


def test_truncation_drops_oldest_first():
    history = [
        HistoryItem(role="user", type="query", content="old" * 30),
        HistoryItem(role="assistant", type="plan", content="mid" * 10),
        HistoryItem(role="tool", type="tool_result", content="new" * 10),
    ]

    truncated = truncate_history(history, max_tokens=18)

    assert len(truncated) <= len(history)
    assert all(item.type != "query" for item in truncated)
