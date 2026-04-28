"""Client for calling agents embeddings service."""

import logging
from typing import List

import requests

logger = logging.getLogger(__name__)


class AgentsEmbeddingsClient:
    """HTTP client for embeddings service in agents."""

    def __init__(self, base_url: str = "http://agents:8003"):
        """
        Initialize embeddings client.

        Args:
            base_url: agents service URL (default: agents:8003)
        """
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v2/embeddings"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts.

        Args:
            texts: list of texts to embed

        Returns:
            list of embedding vectors (one per input text, same order)

        Raises:
            RuntimeError: on network error or service failure
            ValueError: if response format invalid or count mismatch
        """
        if not texts:
            return []

        try:
            response = requests.post(
                self.endpoint,
                json={"texts": texts},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.error(
                "Embeddings request failed (endpoint=%s): %s", self.endpoint, exc
            )
            raise RuntimeError(f"Embeddings request failed: {exc}") from exc

        try:
            data = response.json()
            embeddings = data.get("embeddings")

            if embeddings is None:
                raise ValueError("Missing 'embeddings' in response")

            if not isinstance(embeddings, list):
                raise ValueError(f"'embeddings' must be list, got {type(embeddings)}")

            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Embedding count mismatch: got {len(embeddings)}, expected {len(texts)}"
                )

            return embeddings
        except ValueError as exc:
            logger.error("Invalid embeddings response: %s", exc)
            raise RuntimeError(f"Invalid embeddings response: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error parsing embeddings response: %s", exc)
            raise RuntimeError(f"Response parsing failed: {exc}") from exc
