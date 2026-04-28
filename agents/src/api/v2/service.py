"""Service layer for v2 API endpoints."""

from __future__ import annotations

import logging
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
from providers.factory import ProviderFactory
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

logger = logging.getLogger(__name__)

_DEFAULT_KEEP_ALIVE = "0s"


def resolve_keep_alive() -> str:
    """
    Resolve keep_alive parameter from environment variable.
    
    Returns:
        Keep alive duration string
    """
    raw = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", _DEFAULT_KEEP_ALIVE).strip()
    result = raw if raw else _DEFAULT_KEEP_ALIVE
    logger.debug("Resolved keep_alive: %s", result)
    return result


class V2RuntimeServices:
    """Factory for standardized v2 services using a shared Ollama client."""

    def __init__(self, keep_alive: str | None = None) -> None:
        """
        Initialize runtime services with shared Ollama client.
        
        Args:
            keep_alive: Ollama keep_alive parameter
        """
        self.keep_alive = keep_alive or resolve_keep_alive()
        logger.info("[V2RuntimeServices] Initializing with keep_alive=%s", self.keep_alive)
        
        # Create provider instances for each service using the registry
        from models.registry import (
            EVALUATOR_MODEL, PLANNER_MODEL, DOMAIN_CRITIC_MODEL, 
            INSIGHTS_MODEL, EMBEDDING_MODEL, CIF_MODEL
        )
        
        # Get fallback chains for each service
        from models import get_fallback_chain
        
        # Create providers with fallback support
        evaluator_fallback_chain = get_fallback_chain("evaluator")
        planner_fallback_chain = get_fallback_chain("planner")
        domain_critic_fallback_chain = get_fallback_chain("domain_critic")
        insights_fallback_chain = get_fallback_chain("insights")
        embedding_fallback_chain = get_fallback_chain("embedding")
        cif_fallback_chain = get_fallback_chain("cif")
        
        # Create providers with fallback support
        self.evaluator_provider = ProviderFactory.get_provider_with_fallback(
            EVALUATOR_MODEL, evaluator_fallback_chain
        )
        self.planner_provider = ProviderFactory.get_provider_with_fallback(
            PLANNER_MODEL, planner_fallback_chain
        )
        self.domain_critic_provider = ProviderFactory.get_provider_with_fallback(
            DOMAIN_CRITIC_MODEL, domain_critic_fallback_chain
        )
        self.insights_provider = ProviderFactory.get_provider_with_fallback(
            INSIGHTS_MODEL, insights_fallback_chain
        )
        self.embedding_provider = ProviderFactory.get_provider_with_fallback(
            EMBEDDING_MODEL, embedding_fallback_chain
        )
        self.cif_provider = ProviderFactory.get_provider_with_fallback(
            CIF_MODEL, cif_fallback_chain
        )
        
        # Create services using providers
        self.chat = ChatService(llm_provider=self.evaluator_provider)
        self.cif = CifService(llm_provider=self.cif_provider)
        self.crystal_spec = CrystalSpecExtractionAgent(
            llm_provider=self.cif_provider,
        )
        self.embeddings = EmbeddingsService(
            model_name=EMBEDDING_MODEL,
            llm_provider=self.embedding_provider,
        )
        self.decision = DecisionService(
            model_name=PLANNING_EVALUATOR_MODEL,
            llm_provider=self.evaluator_provider,
        )
        self.planning_evaluator = PlanningEvaluatorService(
            model_name=PLANNING_EVALUATOR_MODEL,
            llm_provider=self.planner_provider,
        )
        self.domain_critic = DomainCriticService(
            model_name=DOMAIN_CRITIC_MODEL,
            llm_provider=self.domain_critic_provider,
        )
        self.insights = InsightsService(
            model_name=INSIGHTS_MODEL,
            llm_provider=self.insights_provider,
        )
        self.info = InfoService()
        logger.info("[V2RuntimeServices] All services initialized successfully")

    def download_models(self) -> None:
        """Download required models."""
        logger.info("[V2RuntimeServices] Starting model download")
        # For backward compatibility, we'll still use the loader service
        # but we'll need to update it to work with the new provider system
        from services import LoadModelsService
        from services.ollama_client import OllamaClient
        self.loader = LoadModelsService(ollama_client=OllamaClient(keep_alive=self.keep_alive))
        self.loader.download_models()
        logger.info("[V2RuntimeServices] Model download completed")


class EmbeddingsService:
    """Stateless embeddings service for v2 endpoints."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        llm_provider = None,
        keep_alive: str = "0s",
        client: OllamaClient | None = None,
    ) -> None:
        """
        Initialize embeddings service.
        
        Args:
            model_name: Name of the embedding model to use
            llm_provider: LLMProvider instance for embeddings
            keep_alive: Ollama keep_alive parameter (for backward compatibility)
            client: Optional Ollama client instance (for backward compatibility)
        """
        self.model_name = model_name
        # Use the provided llm_provider or fall back to OllamaClient for backward compatibility
        if llm_provider is not None:
            self.provider = llm_provider
        elif client is not None:
            self.provider = client
        else:
            from services.ollama_client import OllamaClient as OllamaClientClass
            self.provider = OllamaClientClass(keep_alive=keep_alive)
        logger.debug(
            "[EmbeddingsService] Initialized with model=%s", self.model_name
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            RuntimeError: If embedding count mismatch occurs
        """
        if not texts:
            logger.debug("[EmbeddingsService] Empty texts list received")
            return []

        logger.info("[EmbeddingsService] Embedding %d texts", len(texts))
        embeddings = self.provider.embed_batch(self.model_name, texts)
        
        if len(embeddings) != len(texts):
            logger.error(
                "[EmbeddingsService] Count mismatch: got %d embeddings for %d texts",
                len(embeddings),
                len(texts),
            )
            raise RuntimeError(
                f"Embedding count mismatch: got {len(embeddings)}, expected {len(texts)}"
            )
        
        logger.info("[EmbeddingsService] Successfully embedded %d texts", len(texts))
        return embeddings


class DecisionService:
    """Decision service wrapper around the decision model."""

    def __init__(self, model_name: str, llm_provider = None, ollama_client: OllamaClient = None) -> None:
        """
        Initialize decision service.
        
        Args:
            model_name: Name of the decision model
            llm_provider: LLMProvider instance
            ollama_client: Ollama client instance (for backward compatibility)
        """
        self._model = DecisionModel(model_name=model_name, llm_provider=llm_provider, ollama_client=ollama_client)
        logger.debug("[DecisionService] Initialized with model=%s", model_name)

    def call(self, payload: DecisionModelInput) -> DecisionModelOutput:
        """
        Execute decision model.
        
        Args:
            payload: Decision model input
            
        Returns:
            Decision model output
        """
        logger.info("[DecisionService] Executing decision model")
        result = self._model.call(payload)
        logger.info("[DecisionService] Decision completed: action=%s", result.action)
        return result


class PlanningEvaluatorService:
    """Planning/evaluation wrapper around a single model with mode-specific prompts."""

    def __init__(self, model_name: str, llm_provider = None, ollama_client: OllamaClient = None) -> None:
        """
        Initialize planning/evaluator service.
        
        Args:
            model_name: Name of the planning/evaluator model
            llm_provider: LLMProvider instance
            ollama_client: Ollama client instance (for backward compatibility)
        """
        self._model = PlanningEvaluatorModel(
            model_name=model_name, llm_provider=llm_provider, ollama_client=ollama_client
        )
        logger.debug(
            "[PlanningEvaluatorService] Initialized with model=%s", model_name
        )

    def call(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        """
        Execute planning or evaluation.
        
        Args:
            payload: Planning/evaluation request
            
        Returns:
            Planning/evaluation output
        """
        logger.info("[PlanningEvaluatorService] Executing in mode=%s", payload.mode)
        result = self._model.call(payload)
        logger.info(
            "[PlanningEvaluatorService] Completed: mode=%s | steps=%d",
            payload.mode,
            len(result.steps),
        )
        return result


class DomainCriticService:
    """Domain critic wrapper around dedicated model and endpoint."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        """
        Initialize domain critic service.
        
        Args:
            model_name: Name of the domain critic model
            ollama_client: Ollama client instance
        """
        self._model = DomainCriticModel(
            model_name=model_name, ollama_client=ollama_client
        )
        logger.debug("[DomainCriticService] Initialized with model=%s", model_name)

    def call(self, payload: DomainCriticRequest) -> DomainCriticResponse:
        """
        Execute domain critic.
        
        Args:
            payload: Domain critic request
            
        Returns:
            Domain critic response
        """
        logger.info("[DomainCriticService] Executing domain critic")
        result = self._model.call(payload)
        logger.info("[DomainCriticService] Critic completed")
        return result


class InsightsService:
    """Insights service wrapper around the insights model."""

    def __init__(self, model_name: str, ollama_client: OllamaClient) -> None:
        """
        Initialize insights service.
        
        Args:
            model_name: Name of the insights model
            ollama_client: Ollama client instance
        """
        self._model = InsightsModel(model_name=model_name, ollama_client=ollama_client)
        logger.debug("[InsightsService] Initialized with model=%s", model_name)

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
        """
        Extract insights from document chunk.
        
        Args:
            query: Search query
            title: Document title
            section: Document section
            page: Page number
            chunk: Text chunk to analyze
            max_items: Maximum number of insights to extract
            max_tokens: Maximum tokens for generation
            
        Returns:
            List of extracted insights
        """
        logger.info(
            "[InsightsService] Extracting insights | query_len=%d | chunk_len=%d",
            len(query),
            len(chunk),
        )
        result = self._model.call(
            query=query,
            title=title,
            section=section,
            page=page,
            chunk=chunk,
            max_items=max_items,
            max_tokens=max_tokens,
        )
        logger.info("[InsightsService] Extraction completed | insights_count=%d", len(result))
        return result

    def call(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        return self._model.call(payload)


class DomainCriticService:
    """Domain critic wrapper around dedicated model and endpoint."""

    def __init__(self, model_name: str, llm_provider = None, ollama_client: OllamaClient = None) -> None:
        """
        Initialize domain critic service.
        
        Args:
            model_name: Name of the domain critic model
            llm_provider: LLMProvider instance
            ollama_client: Ollama client instance (for backward compatibility)
        """
        self._model = DomainCriticModel(
            model_name=model_name,
            llm_provider=llm_provider,
            ollama_client=ollama_client,
        )
        logger.debug("[DomainCriticService] Initialized with model=%s", model_name)

    def call(self, payload: DomainCriticRequest) -> DomainCriticResponse:
        """
        Execute domain critic.
        
        Args:
            payload: Domain critic request
            
        Returns:
            Domain critic response
        """
        logger.info("[DomainCriticService] Executing domain critic")
        result = self._model.call(payload)
        logger.info("[DomainCriticService] Critic completed")
        return result


class InsightsService:
    """Insights service wrapper around the insights model."""

    def __init__(
        self,
        model_name: str,
        llm_provider = None,
        ollama_client: OllamaClient = None,
    ) -> None:
        """
        Initialize insights service.
        
        Args:
            model_name: Name of the insights model
            llm_provider: LLMProvider instance
            ollama_client: Ollama client instance (for backward compatibility)
        """
        self._model = InsightsModel(
            model_name=model_name, 
            llm_provider=llm_provider,
            ollama_client=ollama_client
        )

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
        """
        Extract insights from document chunk.
        
        Args:
            query: Search query
            title: Document title
            section: Document section
            page: Page number
            chunk: Text chunk to analyze
            max_items: Maximum number of insights to extract
            max_tokens: Maximum tokens for generation
            
        Returns:
            List of extracted insights
        """
        logger.info(
            "[InsightsService] Extracting insights | query_len=%d | chunk_len=%d",
            len(query),
            len(chunk),
        )
        result = self._model.call(
            query=query,
            title=title,
            section=section,
            page=page,
            chunk=chunk,
            max_items=max_items,
            max_tokens=max_tokens,
        )
        logger.info("[InsightsService] Extraction completed | insights_count=%d", len(result))
        return result

    def call(self, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
        return self._model.call(payload)
