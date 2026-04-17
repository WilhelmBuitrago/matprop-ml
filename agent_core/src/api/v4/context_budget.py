from __future__ import annotations

import json
from typing import Any

from shared.nlp.tokenizer import tokenize


_RELEVANT_HISTORY_TYPES = {
    "query",
    "plan",
    "tool_call",
    "tool_result",
    "evaluation",
    "domain_critic",
}


class ContextBudget:
    """Single source of truth for context sizing and truncation."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max(1, int(max_tokens))

    def estimate_text_tokens(self, text: str) -> int:
        cleaned = str(text or "").strip()
        if not cleaned:
            return 1
        return max(1, len(tokenize(cleaned)))

    def estimate_item_tokens(self, item: Any) -> int:
        payload = self._to_payload(item)
        content = str(payload.get("content", "") or "")
        metadata = payload.get("metadata", {})
        metadata_text = json.dumps(metadata, ensure_ascii=True, sort_keys=True)
        return self.estimate_text_tokens(content) + self.estimate_text_tokens(metadata_text)

    def truncate_history(self, history: list[Any]) -> list[Any]:
        tokens = 0
        result: list[Any] = []

        for item in reversed(history):
            payload = self._to_payload(item)
            item_type = str(payload.get("type", "")).strip()
            if item_type and item_type not in _RELEVANT_HISTORY_TYPES:
                continue

            item_tokens = self.estimate_item_tokens(item)
            if tokens + item_tokens > self.max_tokens:
                continue
            result.append(item)
            tokens += item_tokens

            if tokens >= self.max_tokens:
                break

        return list(reversed(result))

    def truncate_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        tokens = 0
        result: list[dict[str, str]] = []

        for message in reversed(messages):
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role not in {"system", "user", "assistant", "tool"}:
                continue
            if not content:
                continue

            item_tokens = self.estimate_text_tokens(content)
            if tokens + item_tokens > self.max_tokens:
                continue

            result.append({"role": role, "content": content})
            tokens += item_tokens

            if tokens >= self.max_tokens:
                break

        return list(reversed(result))

    def truncate_text(self, text: str, max_tokens: int | None = None) -> str:
        budget = self.max_tokens if max_tokens is None else max(1, int(max_tokens))
        words = tokenize(str(text or ""))
        if len(words) <= budget:
            return str(text or "")
        return " ".join(words[-budget:])

    def summarize_reasoning_steps(self, execution_trace: list[Any], max_steps: int = 6) -> list[str]:
        selected: list[str] = []
        for entry in reversed(execution_trace):
            event = str(getattr(entry, "event", "") or "")
            if event not in {"tool_result", "evaluation", "plan_modified", "stop"}:
                continue
            trace_text = str(getattr(entry, "trace_model", "") or "").strip()
            payload = getattr(entry, "payload", {})
            payload_text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            segment = trace_text or payload_text
            if not segment:
                continue
            selected.append(self.truncate_text(segment, max_tokens=48))
            if len(selected) >= max_steps:
                break
        return list(reversed(selected))

    @staticmethod
    def _to_payload(item: Any) -> dict[str, Any]:
        if hasattr(item, "to_dict"):
            raw = item.to_dict()
            if isinstance(raw, dict):
                return raw
        if isinstance(item, dict):
            return item
        return {"content": str(item)}
