"""Service layer for v2 API endpoints."""

from __future__ import annotations

import os
from typing import Any, List

from models import (
    DOMAIN_CRITIC_MODEL,
    EMBEDDING_MODEL,
    INSIGHTS_MODEL,
    PLANNING_EVALUATOR_MODEL,
)
from services import (
    ChatService,
    CifService,
    CrystalSpecExtractionAgent,
    InfoService,
    LoadModelsService,
    OllamaClient,
)
from .models import (
    DecisionModel,
    DomainCriticModel,
    InsightsModel,
    PlanningEvaluatorModel,
)
from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    DomainCriticRequest,
    DomainCriticResponse,
    PlanningEvaluatorOutput,
    PlanningEvaluatorRequest,
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
            model_name=PLANNING_EVALUATOR_MODEL,
            ollama_client=self.ollama_client,
        )
        self.planning_evaluator = PlanningEvaluatorService(
            model_name=PLANNING_EVALUATOR_MODEL,
            ollama_client=self.ollama_client,
        )
        self.domain_critic = DomainCriticService(
            model_name=DOMAIN_CRITIC_MODEL,
            ollama_client=self.ollama_client,
        )
        self.insights = InsightsService(
            model_name=INSIGHTS_MODEL,
            ollama_client=self.ollama_client,
        )
        self.info = InfoService()

    def download_models(self) -> None:
        self.loader.download_models()


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


class PlanningEvaluatorService:
    """Planning/evaluation wrapper around a single model with mode-specific prompts."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        self._model = PlanningEvaluatorModel(
            model_name=model_name,
            ollama_client=ollama_client,
        )

    def call(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        return self._model.call(payload)


class DomainCriticService:
    """Domain critic wrapper around dedicated model and endpoint."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        self._model = DomainCriticModel(
            model_name=model_name,
            ollama_client=ollama_client,
        )

    def call(self, payload: DomainCriticRequest) -> DomainCriticResponse:
        return self._model.call(payload)


class InsightsService:
    """Insights service wrapper around the insights model."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str,
    ) -> None:
        self._model = InsightsModel(model_name=model_name, ollama_client=ollama_client)

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
        return self._model.call(
            query=query,
            title=title,
            section=section,
            page=page,
            chunk=chunk,
            max_items=max_items,
            max_tokens=max_tokens,
        )
