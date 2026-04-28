"""Client for crystal generation and extraction endpoints in agents service."""

from __future__ import annotations

import os
from typing import Any

import requests


class AgentsCrystalClient:
    def __init__(self, base_url: str | None = None) -> None:
        resolved_base_url = base_url or os.getenv("AGENTS_URL", "http://agents:8003")
        self.base_url = resolved_base_url.rstrip("/")
        self.spec_endpoint = f"{self.base_url}/v2/crystal/spec"
        self.complete_endpoint = f"{self.base_url}/v2/crystal/complete"

    def extract_spec(
        self, query: str, deterministic_spec: dict[str, Any]
    ) -> dict[str, Any]:
        response = requests.post(
            self.spec_endpoint,
            json={
                "query": query,
                "deterministic_spec": deterministic_spec,
            },
        )
        response.raise_for_status()
        return response.json()

    def generate(
        self,
        *,
        system_message: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        stop_tokens: list[str] | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "system_message": system_message,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop_tokens": stop_tokens or [],
        }
        if model_name:
            payload["model_name"] = model_name

        response = requests.post(self.complete_endpoint, json=payload)
        response.raise_for_status()
        return response.json()
