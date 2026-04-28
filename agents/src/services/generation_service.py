"""Generation services backed by OllamaClient."""

from __future__ import annotations

from typing import Any, Dict, List

from models import GENERATION_MODELS
from .ollama_client import OllamaClient


class ChatService:
    """Chat completion service using the configured generation model."""

    def __init__(
        self,
        ollama_client: OllamaClient = None,
        model_name: str | None = None,
        llm_provider = None,
    ) -> None:
        self._client = ollama_client
        self._provider = llm_provider
        self._model_name = model_name or GENERATION_MODELS["final"]

    def chat(
        self,
        history: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        model_name: str | None = None,
        stop_tokens: List[str] | None = None,
    ) -> str:
        options = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if stop_tokens:
            options["stop"] = stop_tokens

        # Use the provider if available, otherwise fall back to client
        provider_or_client = self._provider or self._client
        if provider_or_client is None:
            raise ValueError("No provider or client available for chat service")
            
        response = provider_or_client.chat(
            model=model_name or self._model_name,
            messages=history,
            options=options,
        )
        return response.get("message", {}).get("content", "")


class CifService:
    """CIF generation service using the configured CIF model."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str | None = None,
        llm_provider = None,
    ) -> None:
        self._client = ollama_client
        self._provider = llm_provider
        self._model_name = model_name or GENERATION_MODELS["cif"]

    def get_cif(self, compound_name: str, max_tokens: int = 512) -> str:
        prompt = (
            "Provide the CIF file content for the compound: "
            f"{compound_name}. Only return the CIF content without any additional text."
        )
        
        # Use the provider if available, otherwise fall back to client
        provider_or_client = self._provider or self._client
        if provider_or_client is None:
            raise ValueError("No provider or client available for CIF service")
            
        response = provider_or_client.chat(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": max_tokens},
        )
        return response.get("message", {}).get("content", "")

    def generate_from_prompt(
        self,
        *,
        system_message: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 768,
        stop_tokens: List[str] | None = None,
        model_name: str | None = None,
    ) -> str:
        options: Dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if stop_tokens:
            options["stop"] = stop_tokens

        # Use the provider if available, otherwise fall back to client
        provider_or_client = self._provider or self._client
        if provider_or_client is None:
            raise ValueError("No provider or client available for CIF service")
            
        response = provider_or_client.chat(
            model=model_name or self._model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
            options=options,
        )
        return response.get("message", {}).get("content", "")


class InfoService:
    """Info endpoint payload builder."""

    def __init__(self, chat_model_name: str | None = None) -> None:
        self._chat_model_name = chat_model_name or GENERATION_MODELS["final"]

    def get_info(self) -> Dict[str, Any]:
        return {
            "service": "agent_policy_ollama",
            "ChatService": {
                "Model": self._chat_model_name,
                "Version": "2.0.0",
            },
            "policy_version": "removed_from_runtime",
        }
