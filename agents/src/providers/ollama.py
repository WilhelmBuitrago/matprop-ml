"""Ollama provider implementation using direct HTTP calls to the Ollama API."""
import json
import logging
import time
from services.backend_config.client import client as config
from typing import Any, Dict, List, Optional, Set

import httpx

from .base import LLMProvider
from .exceptions import (
    LLMProviderError,
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama provider implementation using direct Ollama API calls.

    Each method maps onto a specific Ollama REST endpoint:

    - :meth:`chat` -> ``POST /api/chat``
    - :meth:`embed` -> ``POST /api/embeddings``
    - :meth:`list_model_names` -> ``GET /api/tags``
    - :meth:`pull_model` -> ``POST /api/pull``
    """

    #: Default timeout (seconds) for HTTP requests to the Ollama API.
    DEFAULT_TIMEOUT: float = 120.0

    #: Default keep_alive value (unload model immediately after each request).
    DEFAULT_KEEP_ALIVE: str = "0s"

    def __init__(self, keep_alive: str = "0s", timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Ollama provider.

        Args:
            keep_alive: Ollama keep_alive parameter (memory management)
            timeout: HTTP request timeout in seconds
        """
        self.keep_alive = keep_alive or self.DEFAULT_KEEP_ALIVE
        self.timeout = timeout
        self.ollama_host = config.get(
            "system.extra_config.ollama_host", "http://localhost:11434"
        )

        self.client = httpx.Client(
            base_url=self.ollama_host,
            timeout=self.timeout,
        )
        logger.debug(
            "OllamaProvider initialized with keep_alive=%s, host=%s, timeout=%s",
            self.keep_alive,
            self.ollama_host,
            self.timeout,
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _build_ollama_options(
        self, options: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Translate provider-agnostic options onto Ollama's ``options`` object.

        Recognised option keys (consistent with the rest of the provider family):
            - temperature
            - num_predict  (also accepts the ``max_tokens`` alias)
            - top_p
            - stop         (list of stop sequences)
            - top_k, seed, repeat_penalty, presence_penalty, frequency_penalty

        Any remaining keys are forwarded verbatim so Ollama receives the full
        set of native parameters it accepts.
        """
        if not options:
            return {}

        ollama_options: Dict[str, Any] = {}

        if "temperature" in options:
            ollama_options["temperature"] = options["temperature"]

        if "num_predict" in options:
            ollama_options["num_predict"] = options["num_predict"]
        elif "max_tokens" in options:
            ollama_options["num_predict"] = options["max_tokens"]

        if "top_p" in options:
            ollama_options["top_p"] = options["top_p"]

        if "stop" in options:
            ollama_options["stop"] = options["stop"]

        # Forward any remaining native Ollama options that callers may have set.
        known = {"temperature", "num_predict", "max_tokens", "top_p", "stop"}
        for key, value in options.items():
            if key not in known and key not in ollama_options:
                ollama_options[key] = value

        return ollama_options

    def _map_error(
        self, exc: Exception, *, method: str, model: Optional[str] = None
    ) -> LLMProviderError:
        """Map an httpx exception onto the project's exception hierarchy.

        The check order matters: ``httpx.TimeoutException`` is a subclass of
        ``httpx.RequestError`` so it must be tested first.
        """
        provider = "ollama"

        if isinstance(exc, httpx.TimeoutException):
            logger.error("Ollama timeout on %s: %s", method, exc)
            return ProviderTimeoutError(
                f"Ollama timeout on {method}: {exc}",
                provider=provider,
                model=model,
                timeout_seconds=self.timeout,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code if exc.response else None
            logger.error("Ollama API error on %s (status %s): %s", method, status, exc)
            return ProviderAPIError(
                f"Ollama API error on {method}: {exc}",
                provider=provider,
                model=model,
                status_code=status,
                error_details=str(exc),
            )
        if isinstance(exc, httpx.RequestError):
            logger.error("Ollama connection error on %s: %s", method, exc)
            return ProviderConnectionError(
                f"Ollama connection error on {method}: {exc}",
                provider=provider,
                model=model,
                connection_error=str(exc),
            )
        logger.error("Ollama provider error on %s: %s", method, exc)
        return LLMProviderError(
            f"Ollama provider error on {method}: {exc}",
            provider=provider,
            model=model,
        )

    # ------------------------------------------------------------------ #
    #  Chat
    # ------------------------------------------------------------------ #
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get chat completion from the Ollama API.

        Sends a POST to ``/api/chat`` with ``stream: false`` so that a single
        complete response dict (containing ``message.content``) is returned,
        matching the contract expected by every consumer in this project.

        Args:
            model: Model name to use for completion.
            messages: List of message dicts with ``role`` and ``content``.
            options: Optional model-specific options. Recognised keys:
                ``temperature``, ``num_predict`` (or ``max_tokens``),
                ``top_p``, ``stop``.

        Returns:
            Raw Ollama chat response dict (contains ``message``, ``done``).

        Raises:
            LLMProviderError: on API or network failure (mapped from httpx
                exceptions to the project's exception hierarchy).
        """
        logger.debug("OllamaProvider.chat called with model=%s", model)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
        }

        ollama_options = self._build_ollama_options(options)
        if ollama_options:
            payload["options"] = ollama_options

        logger.debug("Ollama chat payload: %s", json.dumps(payload, ensure_ascii=False))

        start_time = time.time()
        try:
            response = self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time
            self._log_inference("ollama", model, messages, data, duration)

            return data
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.chat failed after %.3fs: %s", duration, e)
            raise self._map_error(e, method="chat", model=model) from e
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.chat failed after %.3fs: %s", duration, e)
            raise LLMProviderError(
                f"Ollama provider error: {e}", provider="ollama", model=model
            ) from e

    # ------------------------------------------------------------------ #
    #  Embeddings
    # ------------------------------------------------------------------ #
    def embed(self, model: str, text: str) -> List[float]:
        """Get embedding vector for a single text from the Ollama API.

        Sends a POST to ``/api/embeddings``.

        Args:
            model: Model name to use for embedding.
            text: Text to embed.

        Returns:
            List of floats representing the embedding.

        Raises:
            LLMProviderError: on API or network failure.
        """
        logger.debug("OllamaProvider.embed called with model=%s", model)

        payload = {
            "model": model,
            "prompt": text,
            "keep_alive": self.keep_alive,
        }

        start_time = time.time()
        try:
            response = self.client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()

            # The legacy /api/embeddings endpoint returns {"embedding": [...]}
            # while the newer /api/embed endpoint returns {"embeddings": [[...]]}.
            # Handle both for forward/backward compatibility.
            embedding = data.get("embedding")
            if embedding is None:
                embeddings_list = data.get("embeddings", [])
                embedding = embeddings_list[0] if embeddings_list else []
            if not embedding:
                logger.warning(
                    "Ollama embeddings response missing 'embedding' key for model=%s",
                    model,
                )

            duration = time.time() - start_time
            logger.info(
                "Embedding Request | provider=ollama | model=%s | "
                "duration=%.3fs | text_length=%d",
                model,
                duration,
                len(text),
            )
            return embedding
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.embed failed after %.3fs: %s", duration, e)
            raise self._map_error(e, method="embed", model=model) from e
        except Exception as e:
            duration = time.time() - start_time
            logger.error("OllamaProvider.embed failed after %.3fs: %s", duration, e)
            raise LLMProviderError(
                f"Ollama provider error: {e}", provider="ollama", model=model
            ) from e

    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts from the Ollama API.

        Ollama's ``/api/embeddings`` endpoint accepts a single prompt per
        request, so batch embedding is performed by calling :meth:`embed`
        sequentially for each text.

        Args:
            model: Model name to use for embedding.
            texts: List of texts to embed.

        Returns:
            List of embedding vectors in the same order as *texts*.

        Raises:
            LLMProviderError: on API or network failure.
        """
        logger.debug(
            "OllamaProvider.embed_batch called with model=%s, texts_count=%d",
            model,
            len(texts),
        )

        embeddings: List[List[float]] = []
        start_time = time.time()
        try:
            for text in texts:
                embeddings.append(self.embed(model, text))

            duration = time.time() - start_time
            logger.info(
                "Embedding Batch Request | provider=ollama | model=%s | "
                "duration=%.3fs | texts_count=%d",
                model,
                duration,
                len(texts),
            )
            return embeddings
        except LLMProviderError:
            # Already mapped by embed() — re-raise as-is.
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "OllamaProvider.embed_batch failed after %.3fs: %s", duration, e
            )
            raise LLMProviderError(
                f"Ollama provider error: {e}", provider="ollama", model=model
            ) from e

    # ------------------------------------------------------------------ #
    #  Model management
    # ------------------------------------------------------------------ #
    def list_model_names(self) -> Set[str]:
        """Return installed model names from the Ollama runtime.

        Sends a GET to ``/api/tags``.

        Returns:
            Set of model names available in the local Ollama runtime.

        Raises:
            LLMProviderError: on API or network failure.
        """
        logger.debug("OllamaProvider.list_model_names called")

        start_time = time.time()
        try:
            response = self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time
            logger.info("List models | provider=ollama | duration=%.3fs", duration)

            models = data.get("models", [])
            return {
                str(model.get("name", ""))
                for model in models
                if model.get("name")
            }
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            logger.error(
                "OllamaProvider.list_model_names failed after %.3fs: %s",
                duration,
                e,
            )
            raise self._map_error(e, method="list_model_names") from e
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "OllamaProvider.list_model_names failed after %.3fs: %s",
                duration,
                e,
            )
            raise LLMProviderError(
                f"Ollama provider error: {e}", provider="ollama"
            ) from e

    def pull_model(self, model_name: str) -> None:
        """Pull a model into the local Ollama runtime.

        Sends a POST to ``/api/pull`` with ``stream: false`` so a single
        terminal response is returned.

        Args:
            model_name: Name of the model to pull.

        Raises:
            LLMProviderError: on API or network failure.
        """
        logger.debug("OllamaProvider.pull_model called with model_name=%s", model_name)

        payload = {
            "name": model_name,
            "stream": False,
        }

        start_time = time.time()
        try:
            response = self.client.post("/api/pull", json=payload)
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time
            logger.info(
                "Pull model | provider=ollama | model=%s | duration=%.3fs | status=%s",
                model_name,
                duration,
                data.get("status", "unknown"),
            )
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            logger.error(
                "OllamaProvider.pull_model failed after %.3fs: %s", duration, e
            )
            raise self._map_error(
                e, method="pull_model", model=model_name
            ) from e
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "OllamaProvider.pull_model failed after %.3fs: %s", duration, e
            )
            raise LLMProviderError(
                f"Ollama provider error: {e}", provider="ollama", model=model_name
            ) from e

    # ------------------------------------------------------------------ #
    #  Inference logging
    # ------------------------------------------------------------------ #
    def _log_inference(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, str]],
        response: Dict[str, Any],
        duration: float,
    ) -> None:
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
