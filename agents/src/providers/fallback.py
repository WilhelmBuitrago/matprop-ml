"""Fallback inference manager for handling provider failover."""
import logging
from typing import Any, Dict, List, Optional, Set
from .base import LLMProvider
from .exceptions import (
    LLMProviderError,
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError
)

logger = logging.getLogger(__name__)


class FallbackInferenceManager:
    """Manages fallback logic for LLM provider failover."""
    
    # Default fallback chain: primary -> fallback providers
    DEFAULT_FALLBACK_CHAIN = ["ollama", "openrouter"]
    
    # Error types that trigger fallback
    TRIGGER_ERRORS = (
        ProviderTimeoutError,
        ProviderConnectionError,
        ProviderAPIError,  # This includes auth and quota errors
    )
    
    def __init__(self, primary_provider: LLMProvider, fallback_providers: List[LLMProvider] = None):
        """
        Initialize fallback manager with primary provider and fallback chain.
        
        Args:
            primary_provider: The primary LLMProvider to use
            fallback_providers: List of fallback LLMProvider instances
        """
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers or []
        logger.info("FallbackInferenceManager initialized with %d fallback providers", 
                  len(self.fallback_providers))
    
    def chat_with_fallback(self, model: str, messages: List[Dict[str, str]], 
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute chat with fallback logic.
        
        Args:
            model: Model name to use
            messages: List of message dictionaries
            options: Optional model-specific options
            
        Returns:
            Dictionary containing the response
            
        Raises:
            LLMProviderError: If all providers fail
        """
        # Try primary provider first
        try:
            logger.debug("Attempting chat with primary provider")
            result = self.primary_provider.chat(model, messages, options)
            logger.debug("Primary provider chat successful")
            return result
        except self.TRIGGER_ERRORS as e:
            logger.warning("Primary provider failed: %s. Attempting fallback.", e)
            self._log_fallback_event("chat", model, str(e))
            
            # Try fallback providers in order
            for i, fallback_provider in enumerate(self.fallback_providers):
                try:
                    logger.debug("Attempting chat with fallback provider %d", i)
                    result = fallback_provider.chat(model, messages, options)
                    logger.info("Fallback provider %d succeeded", i)
                    self._log_fallback_success("chat", model, i)
                    return result
                except self.TRIGGER_ERRORS as fallback_error:
                    logger.warning("Fallback provider %d failed: %s", i, fallback_error)
                    self._log_fallback_event("chat", model, str(fallback_error), fallback_index=i)
                    continue  # Try next fallback
            
            # All providers failed
            logger.error("All providers failed for chat operation")
            raise LLMProviderError(f"All providers failed for chat operation: {e}") from e
    
    def embed_with_fallback(self, model: str, text: str) -> List[float]:
        """
        Execute embed with fallback logic.
        
        Args:
            model: Model name to use
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
            
        Raises:
            LLMProviderError: If all providers fail
        """
        # Try primary provider first
        try:
            logger.debug("Attempting embed with primary provider")
            result = self.primary_provider.embed(model, text)
            logger.debug("Primary provider embed successful")
            return result
        except self.TRIGGER_ERRORS as e:
            logger.warning("Primary provider failed: %s. Attempting fallback.", e)
            self._log_fallback_event("embed", model, str(e))
            
            # Try fallback providers in order
            for i, fallback_provider in enumerate(self.fallback_providers):
                try:
                    logger.debug("Attempting embed with fallback provider %d", i)
                    result = fallback_provider.embed(model, text)
                    logger.info("Fallback provider %d succeeded", i)
                    self._log_fallback_success("embed", model, i)
                    return result
                except self.TRIGGER_ERRORS as fallback_error:
                    logger.warning("Fallback provider %d failed: %s", i, fallback_error)
                    self._log_fallback_event("embed", model, str(fallback_error), fallback_index=i)
                    continue  # Try next fallback
            
            # All providers failed
            logger.error("All providers failed for embed operation")
            raise LLMProviderError(f"All providers failed for embed operation: {e}") from e
    
    def embed_batch_with_fallback(self, model: str, texts: List[str]) -> List[List[float]]:
        """
        Execute embed_batch with fallback logic.
        
        Args:
            model: Model name to use
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            LLMProviderError: If all providers fail
        """
        # Try primary provider first
        try:
            logger.debug("Attempting embed_batch with primary provider")
            result = self.primary_provider.embed_batch(model, texts)
            logger.debug("Primary provider embed_batch successful")
            return result
        except self.TRIGGER_ERRORS as e:
            logger.warning("Primary provider failed: %s. Attempting fallback.", e)
            self._log_fallback_event("embed_batch", model, str(e))
            
            # Try fallback providers in order
            for i, fallback_provider in enumerate(self.fallback_providers):
                try:
                    logger.debug("Attempting embed_batch with fallback provider %d", i)
                    result = fallback_provider.embed_batch(model, texts)
                    logger.info("Fallback provider %d succeeded", i)
                    self._log_fallback_success("embed_batch", model, i)
                    return result
                except self.TRIGGER_ERRORS as fallback_error:
                    logger.warning("Fallback provider %d failed: %s", i, fallback_error)
                    self._log_fallback_event("embed_batch", model, str(fallback_error), fallback_index=i)
                    continue  # Try next fallback
            
            # All providers failed
            logger.error("All providers failed for embed_batch operation")
            raise LLMProviderError(f"All providers failed for embed_batch operation: {e}") from e
    
    def _log_fallback_event(self, operation: str, model: str, error: str, fallback_index: int = None) -> None:
        """Log fallback events for monitoring."""
        if fallback_index is not None:
            logger.warning(
                f"Fallback triggered | operation={operation} | model={model} | "
                f"fallback_index={fallback_index} | error={error}"
            )
        else:
            logger.warning(
                f"Fallback triggered | operation={operation} | model={model} | "
                f"primary_failed=true | error={error}"
            )
    
    def _log_fallback_success(self, operation: str, model: str, fallback_index: int) -> None:
        """Log successful fallback for monitoring."""
        logger.info(
            f"Fallback successful | operation={operation} | model={model} | "
            f"fallback_index={fallback_index}"
        )