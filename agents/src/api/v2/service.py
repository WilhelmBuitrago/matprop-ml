"""Service layer for v2 API endpoints."""

from __future__ import annotations

import json
import os
from typing import Any, List

from models import EMBEDDING_MODEL, GENERATION_MODELS
from services import (
    ChatService,
    CrystalSpecExtractionAgent,
    CifService,
    InfoService,
    LoadModelsService,
    OllamaClient,
)
from .models import DecisionModel, EvaluatorModel
from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
)

_DEFAULT_KEEP_ALIVE = "0s"


def resolve_keep_alive() -> str:
    raw = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", _DEFAULT_KEEP_ALIVE).strip()
    return raw if raw else _DEFAULT_KEEP_ALIVE


class V2RuntimeServices:
    """Factory for standardized v2 services using a shared Ollama client."""

    def __init__(self, keep_alive: str | None = None) -> None:
        self.keep_alive = keep_alive or resolve_keep_alive()
        self.ollama_client = OllamaClient(keep_alive=self.keep_alive)
        self.evaluator_model_name = GENERATION_MODELS["evaluator"]
        self.loader = LoadModelsService(ollama_client=self.ollama_client)
        self.chat = ChatService(ollama_client=self.ollama_client)
        self.cif = CifService(ollama_client=self.ollama_client)
        self.crystal_spec = CrystalSpecExtractionAgent(
            ollama_client=self.ollama_client,
        )
        self.embeddings = EmbeddingsService(
            model=EMBEDDING_MODEL,
            keep_alive=self.keep_alive,
            client=self.ollama_client,
        )
        self.decision = DecisionService(
            model_name=self.evaluator_model_name,
            ollama_client=self.ollama_client,
        )
        self.evaluator = EvaluatorService(
            model_name=self.evaluator_model_name,
            ollama_client=self.ollama_client,
        )
        self.insights = InsightsService(
            model_name=self.evaluator_model_name,
            ollama_client=self.ollama_client,
        )
        self.info = InfoService()


class EmbeddingsService:
    """Stateless embeddings service for v2 endpoints."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        keep_alive: str = "0s",
        client: OllamaClient | None = None,
    ):
        self.model = model
        self.client = client or OllamaClient(keep_alive=keep_alive)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        embeddings = self.client.embed_batch(self.model, texts)
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(embeddings)}, expected {len(texts)}"
            )
        return embeddings


class DecisionService:
    """Decision service wrapper around the decision model."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        self._model = DecisionModel(model_name=model_name, ollama_client=ollama_client)

    def call(self, payload: DecisionModelInput) -> DecisionModelOutput:
        return self._model.call(payload)


class EvaluatorService:
    """Evaluator service wrapper around the evaluator model."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        self._model = EvaluatorModel(model_name=model_name, ollama_client=ollama_client)

    def call(self, payload: EvaluatorModelInput) -> EvaluatorModelOutput:
        return self._model.call(payload)


class InsightsService:
    """Insights extraction service using the evaluator model family."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str | None = None,
    ) -> None:
        self._client = ollama_client
        self._model_name = model_name or GENERATION_MODELS["evaluator"]

    def extract_insights(
        self,
        query: str,
        title: str,
        section: str,
        page: int,
        chunk: str,
        max_items: int = 4,
        max_tokens: int = 180,
    ) -> list[str]:
        prompt = (
            "Return strict JSON array of strings. "
            "Each item must be a concise technical fact extracted from the chunk and relevant to the query. "
            f"Use at most {max_items} facts.\n"
            f"Query: {query}\n"
            f"Title: {title}\n"
            f"Section: {section}\n"
            f"Page: {page}\n"
            f"Chunk: {chunk}"
        )
        response = self._client.chat(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": max_tokens},
        )
        text = response.get("message", {}).get("content", "")
        return self._parse_output(text)

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
