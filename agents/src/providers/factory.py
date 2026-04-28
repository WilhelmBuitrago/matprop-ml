"""Provider factory for resolving and caching LLM providers."""
import logging
import os
from typing import Dict, List, Optional, Tuple

from .base import LLMProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from .fallback import FallbackInferenceManager
from .fallback_manager import FallbackManager

logger = logging.getLogger(__name__)

# Cache for provider instances
_provider_cache: Dict[str, LLMProvider] = {}


def _parse_provider_model(provider_model_str: str) -> tuple[str, str]:
    """Parse provider:model string into provider and model components."""
    if ":" in provider_model_str:
        provider, model = provider_model_str.split(":", 1)
        return provider.strip(), model.strip()
    return provider_model_str, ""


class ProviderFactory:
    """Factory for creating and caching LLM providers."""

    @staticmethod
    def get_provider(provider_model_str: str) -> LLMProvider:
        """
        Get provider instance for provider:model string with caching.
        
        Args:
            provider_model_str: String in format "provider:model" or just "provider"
            
        Returns:
            LLMProvider instance
        """
        logger.debug("ProviderFactory.get_provider called with provider_model_str=%s", 
                   provider_model_str)
        
        # Check cache first
        if provider_model_str in _provider_cache:
            logger.debug("Returning cached provider for %s", provider_model_str)
            return _provider_cache[provider_model_str]
        
        # Parse provider and model
        provider_name, _ = _parse_provider_model(provider_model_str)
        
        # Create provider instance based on provider name
        provider: Optional[LLMProvider] = None
        
        if provider_name == "ollama":
            keep_alive = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", "0s")
            provider = OllamaProvider(keep_alive=keep_alive)
            logger.debug("Created OllamaProvider instance")
        elif provider_name == "openrouter":
            provider = OpenRouterProvider()
            logger.debug("Created OpenRouterProvider instance")
        else:
            # Default to Ollama if not specified
            keep_alive = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", "0s")
            provider = OllamaProvider(keep_alive=keep_alive)
            logger.debug("Created default OllamaProvider instance for unknown provider: %s", 
                       provider_name)
        
        # Cache the provider
        if provider:
            _provider_cache[provider_model_str] = provider
            
        return provider

    @staticmethod
    def get_provider_with_fallback(primary_provider_str: str, fallback_provider_strs: List[str] = None) -> LLMProvider:
        """
        Get provider with fallback chain for failover support.
        
        Args:
            primary_provider_str: Primary provider:model string
            fallback_provider_strs: List of fallback provider:model strings
            
        Returns:
            LLMProvider with fallback support
        """
        logger.debug("ProviderFactory.get_provider_with_fallback called with primary=%s, fallbacks=%s",
                   primary_provider_str, fallback_provider_strs)
        
        # Get primary provider
        primary_provider = ProviderFactory.get_provider(primary_provider_str)
        
        # Get fallback providers
        fallback_providers = []
        if fallback_provider_strs:
            for fallback_str in fallback_provider_strs:
                try:
                    fallback_provider = ProviderFactory.get_provider(fallback_str)
                    fallback_providers.append(fallback_provider)
                except Exception as e:
                    logger.warning("Failed to create fallback provider %s: %s", fallback_str, e)
        
        # Create fallback manager
        fallback_inference_manager = FallbackInferenceManager(
            primary_provider=primary_provider,
            fallback_providers=fallback_providers
        )
        
        # Wrap in FallbackManager to make it implement LLMProvider interface
        return FallbackManager(fallback_inference_manager)

    @staticmethod
    def clear_cache() -> None:
        """Clear the provider cache."""
        global _provider_cache
        _provider_cache = {}
        logger.debug("ProviderFactory cache cleared")