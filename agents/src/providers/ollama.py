"""Ollama provider implementation."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
import httpx

from .base import LLMProvider
from .exceptions import LLMProviderError, ProviderConnectionError, ProviderTimeoutError

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama provider implementation using direct Ollama API calls."""

    def __init__(self, keep_alive: str = "0s"):
        """
        Initialize Ollama provider.
        
        Args:
            keep_alive: Ollama keep_alive parameter (memory management)
        """
        self.keep_alive = keep_alive
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        logger.debug("OllamaProvider initialized with keep_alive=%s", keep_alive)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get chat completion from Ollama."""
        logger.debug("OllamaProvider.chat called with model=%s", model)
        
        start_time = time.time()
        try:
            # Create a simple mock response for now
            # In a real implementation, this would call the Ollama API
            response = {
                "message": {"content": "Mock response from Ollama"},
                "done": True
            }
            
            duration = time.time() - start_time
            
            # Log the inference
            self._log_inference("ollama", model, messages, response, duration)
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.chat failed after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise LLMProviderError(f"Ollama provider error: {e}", provider="ollama", model=model) from e

    def embed(self, model: str, text: str) -> List[float]:
        """Get embedding vector for a single text."""
        logger.debug("OllamaProvider.embed called with model=%s", model)
        
        start_time = time.time()
        try:
            # Create a simple mock response for now
            # In a real implementation, this would call the Ollama API for embeddings
            response = [0.1, 0.2, 0.3, 0.4, 0.5]  # Mock embedding
            
            duration = time.time() - start_time
            
            # Log the inference
            logger.info(
                f"Embedding Request | provider=ollama | model={model} | "
                f"duration={duration:.3f}s | text_length={len(text)}"
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.embed failed after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise LLMProviderError(f"Ollama provider error: {e}", provider="ollama", model=model) from e

    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        logger.debug("OllamaProvider.embed_batch called with model=%s, texts_count=%d", 
                    model, len(texts))
        
        start_time = time.time()
        try:
            # Create a simple mock response for now
            # In a real implementation, this would call the Ollama API for embeddings
            response = [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in texts]  # Mock embeddings
            
            duration = time.time() - start_time
            
            # Log the inference
            logger.info(
                f"Embedding Batch Request | provider=ollama | model={model} | "
                f"duration={duration:.3f}s | texts_count={len(texts)}"
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.embed_batch failed after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise LLMProviderError(f"Ollama provider error: {e}", provider="ollama", model=model) from e

    def list_model_names(self) -> Set[str]:
        """Return installed model names from Ollama runtime."""
        logger.debug("OllamaProvider.list_model_names called")
        try:
            # In a real implementation, this would call the Ollama API to list models
            return {"llama3", "mistral", "deepseek-r1:8b"}
        except Exception as e:
            logger.error("OllamaProvider.list_model_names failed: %s", e)
            # Convert to our custom exception
            raise LLMProviderError(f"Ollama provider error: {e}", provider="ollama") from e

    def pull_model(self, model_name: str) -> None:
        """Pull a model into local Ollama runtime."""
        logger.debug("OllamaProvider.pull_model called with model_name=%s", model_name)
        try:
            # In a real implementation, this would call the Ollama API to pull the model
            logger.info(f"Pulling model {model_name}")
        except Exception as e:
            logger.error("OllamaProvider.pull_model failed: %s", e)
            # Convert to our custom exception
            raise LLMProviderError(f"Ollama provider error: {e}", provider="ollama", model=model_name) from e

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
            f"duration={duration:.3f}s"
        )
        
        # Log detailed request/response for debugging (at debug level)
        logger.debug(
            f"LLM Request/Response | provider={provider_name} | model={model} | "
            f"request={json.dumps(messages, ensure_ascii=False)} | "
            f"response={json.dumps(response, ensure_ascii=False)}"
        )