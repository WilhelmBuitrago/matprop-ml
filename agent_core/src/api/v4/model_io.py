from __future__ import annotations

from typing import Any


def messages_to_history(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Map OpenAI-style messages payload to agents history payload."""
    history: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role in {"system", "user", "assistant", "tool"} and content:
            history.append({"role": role, "content": content})
    return history


def extract_model_text(payload: Any) -> str:
    """Extract text from supported model response shapes."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return payload.get("response") or payload.get("choices", [{}])[0].get(
            "message", {}
        ).get("content", "")
    return str(payload or "")


def clean_model_response(response: str) -> str:
    """Remove chat wrapper artifacts while preserving semantic content."""
    if not response:
        return response

    cleaned = response.strip()

    if cleaned.startswith("Assistant:"):
        cleaned = cleaned[10:].strip()
    if cleaned.startswith("User:"):
        cleaned = cleaned[5:].strip()
    if cleaned.startswith("System:"):
        cleaned = cleaned[7:].strip()

    cleaned = cleaned.replace("[Response]", "").replace("[/Response]", "").strip()

    lines = cleaned.split("\n")
    normalized_lines: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line in {"[Response]", "[/Response]"}:
            continue
        if line.startswith(("User:", "Assistant:", "System:")):
            continue
        normalized_lines.append(line)

    cleaned = "\n".join(normalized_lines).strip()
    if cleaned.endswith(("User:", "Assistant:", "System:")):
        cleaned = (
            cleaned.rsplit("User:", 1)[0]
            .rsplit("Assistant:", 1)[0]
            .rsplit("System:", 1)[0]
            .strip()
        )
    return cleaned
