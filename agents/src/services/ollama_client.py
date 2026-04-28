"""Low-level client for Ollama API calls."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OllamaClient:
    """Thin compatibility wrapper around OllamaProvider for backward compatibility."""

    def __init__(self, keep_alive: str = "0s"):
        """
        Initialize Ollama client compatibility wrapper.
        
        Args:
            keep_alive: Ollama keep_alive parameter (memory management)
        """
        # Import here to avoid circular import
        from providers.ollama import OllamaProvider
        self.provider = OllamaProvider(keep_alive=keep_alive)
        logger.debug("OllamaClient compatibility wrapper initialized with keep_alive=%s", keep_alive)

    def embed(self, model: str, text: str) -> List[float]:
        """
        Get embedding vector for a single text.
        
        Args:
            model: model name (e.g., "mxbai-embed-large")
            text: text to embed
            
        Returns:
            list of floats representing the embedding
            
        Raises:
            RuntimeError: on API or network failure
        """
        try:
            return self.provider.embed(model, text)
        except Exception as exc:
            logger.error("Ollama embed failed for model %s: %s", model, exc)
            raise RuntimeError(f"Embedding request failed: {exc}") from exc

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Get chat completion from Ollama."""
        try:
            return self.provider.chat(model=model, messages=messages, options=options)
        except Exception as exc:
            logger.error("Ollama chat failed for model %s: %s", model, exc)
            raise RuntimeError(f"Chat request failed: {exc}") from exc

    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts sequentially.
        
        Args:
            model: model name
            texts: list of texts to embed
            
        Returns:
            list of embedding vectors (same order as inputs)
            
        Raises:
            RuntimeError: if any embedding fails
        """
        embeddings: List[List[float]] = []
        for i, text in enumerate(texts):
            try:
                embedding = self.embed(model, text)
                embeddings.append(embedding)
            except Exception as exc:
                logger.error("Failed to embed text %d/%d: %s", i + 1, len(texts), exc)
                raise

        return embeddings

    def list_model_names(self) -> set[str]:
        """Return installed model names from Ollama runtime."""
        try:
            return self.provider.list_model_names()
        except Exception as exc:
            logger.error("Failed to list model names: %s", exc)
            raise RuntimeError(f"List models failed: {exc}") from exc

    def pull_model(self, model_name: str) -> None:
        """Pull a model into local Ollama runtime."""
        try:
            self.provider.pull_model(model_name)
        except Exception as exc:
            logger.error("Failed to pull model %s: %s", model_name, exc)
            raise RuntimeError(f"Pull model failed: {exc}") from exc
