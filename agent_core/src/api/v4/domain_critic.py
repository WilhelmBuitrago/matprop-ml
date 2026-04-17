from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import requests

from .context_budget import ContextBudget


DOMAIN_CRITIC_MODEL = "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"
DOMAIN_CRITIC_PROMPT = (
    "Evalua la validez fisica y coherencia de la respuesta.\n\n"
    "NO asumas que los datos son correctos.\n"
    "Detecta:\n"
    "- inconsistencias fisicas\n"
    "- falta de condiciones experimentales\n"
    "- conclusiones no justificadas\n\n"
    "Responde en formato:\n"
    "VALID: <yes/no>\n"
    "CONFIDENCE: <0-1>\n"
    "ISSUES:\n"
    "- ..."
)

logger = logging.getLogger(__name__)


class DomainCriticClient:
    def __init__(
        self,
        *,
        agents_url: str | None = None,
        model_name: str = DOMAIN_CRITIC_MODEL,
        timeout_seconds: int = 45,
        context_budget: ContextBudget | None = None,
    ) -> None:
        base_url = agents_url or os.getenv("AGENTS_URL", "http://agents:8003")
        self._endpoint = f"{base_url.rstrip('/')}/v2/domain-critic"
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._context_budget = context_budget or ContextBudget(max_tokens=2048)

    async def evaluate(
        self,
        *,
        user_query: str,
        tool_results: list[dict[str, Any]],
        reasoning_steps: list[str],
        draft_response: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._evaluate_sync,
            user_query,
            tool_results,
            reasoning_steps,
            draft_response,
        )

    def _evaluate_sync(
        self,
        user_query: str,
        tool_results: list[dict[str, Any]],
        reasoning_steps: list[str],
        draft_response: str,
    ) -> dict[str, Any]:
        compact_reasoning = [
            self._context_budget.truncate_text(step, max_tokens=48)
            for step in reasoning_steps[:8]
            if str(step).strip()
        ]
        payload = {
            "user_query": user_query,
            "model_name": self._model_name,
            "prompt": DOMAIN_CRITIC_PROMPT,
            "tool_results": tool_results,
            "reasoning_steps": compact_reasoning,
            "draft_response": self._context_budget.truncate_text(draft_response, max_tokens=512),
        }

        response = requests.post(
            self._endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        parsed = response.json()
        if isinstance(parsed, dict):
            raw = str(parsed.get("response", parsed.get("content", "")))
        else:
            raw = str(parsed)

        out = parse_domain_critic_response(raw)
        out["raw"] = raw
        return out


def to_domain_critic_tool_result(item: dict[str, Any]) -> dict[str, Any]:
    source = str(item.get("source") or "").strip().lower() or "db"
    if source not in {"db", "paper", "rag", "llm", "simulation"}:
        source = "db"

    confidence_raw = item.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    trace_raw = item.get("trace")
    trace = str(trace_raw).strip() if trace_raw is not None else None
    if trace == "":
        trace = None

    return {
        "status": str(item.get("status") or "").strip() or "error",
        "source": source,
        "confidence": confidence,
        "is_synthetic": bool(item.get("is_synthetic", False)),
        "trace": trace,
        "payload": item.get("payload") if isinstance(item.get("payload"), dict) else {},
        "error_code": item.get("error_code"),
        "error_detail": item.get("error_detail") or item.get("error_message"),
    }


def parse_domain_critic_response(raw: str) -> dict[str, Any]:
    text = str(raw or "")
    valid_match = re.search(r"VALID\s*:\s*(yes|no)", text, flags=re.IGNORECASE)
    confidence_match = re.search(
        r"CONFIDENCE\s*:\s*([01](?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )

    issues: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("ISSUES"):
            capture = True
            continue
        if capture and stripped.startswith("-"):
            issue = stripped[1:].strip()
            if issue:
                issues.append(issue)

    valid = bool(valid_match and valid_match.group(1).lower() == "yes")
    confidence = 0.0
    if confidence_match:
        try:
            confidence = float(confidence_match.group(1))
        except ValueError:
            confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "valid": valid,
        "confidence": confidence,
        "issues": issues,
    }


def tool_results_from_history(history: list[Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for item in history:
        if hasattr(item, "to_dict"):
            payload = item.to_dict()
        elif isinstance(item, dict):
            payload = item
        else:
            continue
        if str(payload.get("type", "")).strip() != "tool_result":
            continue
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            collected.append(to_domain_critic_tool_result(metadata))
    return collected


def default_draft_response(tool_results: list[dict[str, Any]]) -> str:
    if not tool_results:
        return "No tool evidence collected yet."
    return json.dumps(
        {
            "tool_results_count": len(tool_results),
            "latest_tool_result": tool_results[-1],
        },
        ensure_ascii=True,
    )
