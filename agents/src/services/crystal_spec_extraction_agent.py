"""Specialized agent for extracting CrystalSpec fields from query text."""

from __future__ import annotations

import json
from typing import Any

from models import GENERATION_MODELS
from .ollama_client import OllamaClient

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract crystallography intent into strict JSON. "
    "Return only a JSON object with keys: formula, lattice_type, space_group, elements, constraints. "
    "Do not include markdown or explanatory text."
)


class CrystalSpecExtractionAgent:
    """LLM-assisted field completion for partially parsed crystal specs."""

    def __init__(
        self, ollama_client: OllamaClient = None, model_name: str | None = None, llm_provider = None
    ) -> None:
        self._client = ollama_client
        self._provider = llm_provider
        self._model_name = model_name or GENERATION_MODELS["evaluator"]

    def extract(self, query: str, deterministic_spec: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Complete missing crystallography fields from the user query.\n"
            "Use deterministic_spec values as fixed truth and only infer missing values.\n"
            f"query: {query}\n"
            f"deterministic_spec: {json.dumps(deterministic_spec, ensure_ascii=True)}\n"
            "Return JSON now."
        )

        # Use the provider if available, otherwise fall back to client
        provider_or_client = self._provider or self._client
        if provider_or_client is None:
            raise ValueError("No provider or client available for crystal spec extraction agent")
            
        response = provider_or_client.chat(
            model=self._model_name,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1, "num_predict": 320},
        )
        content = response.get("message", {}).get("content", "")
        return self._safe_json(content)

    def _safe_json(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {}

        try:
            payload = json.loads(text)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    payload = json.loads(text[start : end + 1])
                    return payload if isinstance(payload, dict) else {}
                except json.JSONDecodeError:
                    return {}
        return {}
