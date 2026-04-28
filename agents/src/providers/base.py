"""Abstract base class for LLM providers."""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time

from .exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers following the provider pattern."""

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get chat completion from the provider.
        
        Args:
            model: Model name to use for completion
            messages: List of message dictionaries with role and content
            options: Optional model-specific options
            
        Returns:
            Dictionary containing the response with message content
            
        Raises:
            LLMProviderError: on API or network failure
        """
        pass

    @abstractmethod
    def embed(self, model: str, text: str) -> List[float]:
        """
        Get embedding vector for a single text.
        
        Args:
            model: Model name to use for embedding
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
            
        Raises:
            LLMProviderError: on API or network failure
        """
        pass

    @abstractmethod
    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            model: Model name to use for embedding
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (same order as inputs)
            
        Raises:
            LLMProviderError: if any embedding fails
        """
        pass

    @abstractmethod
    def list_model_names(self) -> set[str]:
        """
        Return available model names from the provider.
        
        Returns:
            Set of model names available in the provider
        """
        pass

    @abstractmethod
    def pull_model(self, model_name: str) -> None:
        """
        Pull/preload a model into the provider.
        
        Args:
            model_name: Name of the model to pull
        """
        pass

    def _log_inference(self, provider_name: str, model: str, messages: List[Dict[str, str]], 
                      response: Dict[str, Any], duration: float) -> None:
        """
        Log inference request and response for monitoring and debugging.
        
        Args:
            provider_name: Name of the provider (e.g., "ollama", "openrouter")
            model: Model name used
            messages: Input messages
            response: Response from the provider
            duration: Time taken for the inference in seconds
        """
        # Log the inference for monitoring
        logger.info(
            f"LLM Inference | provider={provider_name} | model={model} | "
            f"duration={duration:.3f}s | input_tokens={self._count_tokens(messages)} | "
            f"output_tokens={self._count_tokens([response.get('message', {})] if response.get('message') else [])}"
        )
        
        # Log detailed request/response for debugging (at debug level)
        logger.debug(
            f"LLM Request/Response | provider={provider_name} | model={model} | "
            f"request={json.dumps(messages, ensure_ascii=False)} | "
            f"response={json.dumps(response, ensure_ascii=False)}"
        )

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Simple token counting approximation."""
        total_chars = sum(len(msg.get('content', '')) for msg in messages)
        # Rough approximation: 1 token ≈ 4 characters
        return total_chars // 4