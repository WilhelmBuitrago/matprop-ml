"""OpenRouter provider implementation."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

import httpx
from .base import LLMProvider
from .exceptions import LLMProviderError, ProviderAPIError, ProviderAuthenticationError, ProviderTimeoutError

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider implementation using httpx for API calls."""

    def __init__(self):
        """Initialize OpenRouter provider."""
        # Try to get API key from centralized configuration first
        try:
            from common.config_client import client as config
            self.api_key = config.get("external_apis.openrouter_api_key")
            if not self.api_key:
                # Fallback to environment variable for backward compatibility
                self.api_key = os.getenv("OPENROUTER_API_KEY")
        except Exception:
            # Fallback to environment variable if config not available
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required in configuration or environment variables")
        
        self.client = httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://matprop-ml.local",  # Optional, for tracking
                "X-Title": "matprop-ml",  # Optional, for display
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
        logger.debug("OpenRouterProvider initialized")

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get chat completion from OpenRouter."""
        logger.debug("OpenRouterProvider.chat called with model=%s", model)
        
        # Map model name from provider:model format to OpenRouter format
        openrouter_model = model
        
        payload = {
            "model": openrouter_model,
            "messages": messages,
        }
        
        # Add options if provided
        if options:
            payload["temperature"] = options.get("temperature", 0.7)
            if "num_predict" in options:
                payload["max_tokens"] = options["num_predict"]
        
        start_time = time.time()
        try:
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            duration = time.time() - start_time
            
            # Log the request and response for debugging
            logger.debug("OpenRouter chat request: %s", json.dumps(payload))
            logger.debug("OpenRouter chat response: %s", json.dumps(data))
            
            # Log the inference
            self._log_inference("openrouter", openrouter_model, messages, data, duration)
            
            return data
        except httpx.HTTPStatusError as e:
            duration = time.time() - start_time
            logger.error("OpenRouter API error after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise ProviderAPIError(
                f"OpenRouter API error: {e}", 
                provider="openrouter", 
                model=model,
                status_code=e.response.status_code if e.response else None,
                error_details=str(e)
            ) from e
        except httpx.TimeoutException as e:
            duration = time.time() - start_time
            logger.error("OpenRouter timeout after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise ProviderTimeoutError(
                f"OpenRouter timeout: {e}", 
                provider="openrouter", 
                model=model,
                timeout_seconds=self.client.timeout.read if self.client.timeout else None
            ) from e
        except httpx.RequestError as e:
            duration = time.time() - start_time
            logger.error("OpenRouter request failed after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise ProviderConnectionError(
                f"OpenRouter connection error: {e}", 
                provider="openrouter", 
                model=model,
                connection_error=str(e)
            ) from e
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OpenRouter request failed after %.3fs: %s", duration, e)
            # Convert to our custom exception
            raise LLMProviderError(
                f"OpenRouter request failed: {e}", 
                provider="openrouter", 
                model=model
            ) from e

    def embed(self, model: str, text: str) -> List[float]:
        """Get embedding - not directly supported by OpenRouter, so we'll raise an error."""
        logger.warning("OpenRouter does not support direct embedding API")
        raise NotImplementedError("OpenRouter does not support direct embedding API. Use a dedicated embedding model.")

    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts - not directly supported by OpenRouter."""
        logger.warning("OpenRouter does not support direct embedding API")
        raise NotImplementedError("OpenRouter does not support direct embedding API. Use a dedicated embedding model.")

    def list_model_names(self) -> Set[str]:
        """Return available model names from OpenRouter."""
        logger.debug("OpenRouterProvider.list_model_names called")
        # OpenRouter doesn't have a simple list endpoint, so we'll return a set of known models
        # In a real implementation, you might want to call their models endpoint
        try:
            response = self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return {model["id"] for model in data.get("data", [])}
        except Exception as e:
            logger.warning("Failed to fetch OpenRouter models: %s", e)
            # Return some common OpenRouter models
            return {
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-3.5-turbo",
                "openai/gpt-4",
                "openai/gpt-4-turbo",
                "google/gemini-pro",
                "google/gemini-flash"
            }

    def pull_model(self, model_name: str) -> None:
        """Pull a model - not applicable for OpenRouter (cloud service)."""
        logger.debug("OpenRouterProvider.pull_model called with model_name=%s (no-op for cloud service)", model_name)
        # No-op for cloud service
        pass