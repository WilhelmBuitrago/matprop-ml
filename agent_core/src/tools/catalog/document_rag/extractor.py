from __future__ import annotations

import json
import os
from typing import Any

import requests

from .errors import ExtractionError
from .models import ChunkScore


class InsightExtractor:
    def __init__(self) -> None:
        self.model_url = os.getenv("AGENTS_URL", "http://agents:8003")

    def extract_for_chunk(self, query: str, chunk: ChunkScore) -> list[str]:
        try:
            response = requests.post(
                f"{self.model_url}/v2/insights",
                json={
                    "query": query,
                    "title": chunk.chunk.title,
                    "section": chunk.chunk.section,
                    "page": chunk.chunk.page,
                    "chunk": chunk.chunk.text,
                    "max_tokens": 180,
                },
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ExtractionError("insights_request_failed") from exc

        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("insights"), list):
            return [
                str(item).strip() for item in payload["insights"] if str(item).strip()
            ]

        return self._parse_output(str(payload))

    def _parse_output(self, text: str) -> list[str]:
        if not text:
            return []

        parsed = self._safe_json(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, dict):
            values = parsed.get("extracted_info") or parsed.get("facts") or []
            if isinstance(values, list):
                return [str(item).strip() for item in values if str(item).strip()]
        return []

    def _safe_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start_list = text.find("[")
            end_list = text.rfind("]")
            if start_list >= 0 and end_list > start_list:
                return json.loads(text[start_list : end_list + 1])
            start_obj = text.find("{")
            end_obj = text.rfind("}")
            if start_obj >= 0 and end_obj > start_obj:
                return json.loads(text[start_obj : end_obj + 1])
        return []
