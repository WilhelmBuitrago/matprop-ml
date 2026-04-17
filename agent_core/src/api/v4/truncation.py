from __future__ import annotations

from typing import Any

from .context_budget import ContextBudget


def estimate_tokens(item: Any) -> int:
    return ContextBudget(max_tokens=4096).estimate_item_tokens(item)


def truncate_history(history: list[Any], max_tokens: int) -> list[Any]:
    return ContextBudget(max_tokens=max_tokens).truncate_history(history)
