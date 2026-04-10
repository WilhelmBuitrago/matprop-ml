from __future__ import annotations

from typing import Any


def estimate_tokens(item: Any) -> int:
    if hasattr(item, "to_dict"):
        payload = item.to_dict()
    elif isinstance(item, dict):
        payload = item
    else:
        payload = {"content": str(item)}

    content = str(payload.get("content", ""))
    metadata = payload.get("metadata", {})
    metadata_text = str(metadata) if isinstance(metadata, dict) else str(metadata)
    return max(1, (len(content) + len(metadata_text)) // 4)


def truncate_history(history: list[Any], max_tokens: int) -> list[Any]:
    tokens = 0
    result: list[Any] = []

    for item in reversed(history):
        item_tokens = estimate_tokens(item)
        if tokens + item_tokens > max_tokens:
            break
        result.append(item)
        tokens += item_tokens

    return list(reversed(result))
