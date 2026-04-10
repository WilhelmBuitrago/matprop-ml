from __future__ import annotations

from .history_item import HistoryItem


def has_tool_results(history: list[HistoryItem]) -> bool:
    return any(item.type == "tool_result" for item in history)


def handle_evaluator_failure(history: list[HistoryItem]) -> str:
    if has_tool_results(history):
        return "final_with_context"
    return "final_without_context"
