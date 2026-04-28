"""Fallback manager that implements LLMProvider interface with failover logic."""
import logging
from typing import Any, Dict, List, Optional
from .base import LLMProvider
from .exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class FallbackManager(LLMProvider):
    """LLMProvider implementation that wraps a primary provider with fallback logic."""
    
    def __init__(self, fallback_inference_manager):
        """
        Initialize fallback manager.
        
        Args:
            fallback_inference_manager: FallbackInferenceManager instance
        """
        self.fallback_inference_manager = fallback_inference_manager
        logger.debug("FallbackManager initialized")
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute chat with fallback logic.
        
        Args:
            model: Model name to use for completion
            messages: List of message dictionaries with role and content
            options: Optional model-specific options
            
        Returns:
            Dictionary containing the response with message content
        """
        return self.fallback_inference_manager.chat_with_fallback(model, messages, options)
    
    def embed(self, model: str, text: str) -> List[float]:
        """
        Get embedding with fallback logic.
        
        Args:
            model: Model name to use for embedding
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        return self.fallback_inference_manager.embed_with_fallback(model, text)
    
    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings with fallback logic.
        
        Args:
            model: Model name to use for embedding
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (same order as inputs)
        """
        return self.fallback_inference_manager.embed_batch_with_fallback(model, texts)
    
    def list_model_names(self) -> set[str]:
        """
        List model names - delegates to primary provider.
        
        Returns:
            Set of model names available in the primary provider
        """
        # For list_model_names, we just delegate to the primary provider
        # Fallback would be complex to implement correctly
        return self.fallback_inference_manager.primary_provider.list_model_names()
    
    def pull_model(self, model_name: str) -> None:
        """
        Pull model - delegates to primary provider.
        
        Args:
            model_name: Name of the model to pull
        """
        # For pull_model, we just delegate to the primary provider
        # Fallback would be complex to implement correctly
        self.fallback_inference_manager.primary_provider.pull_model(model_name)