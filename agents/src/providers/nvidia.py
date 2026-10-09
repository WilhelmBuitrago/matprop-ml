"""NVIDIA NIM provider implementation using the OpenAI-compatible SDK.

This provider talks to the NVIDIA API at https://integrate.api.nvidia.com/v1
using the OpenAI Python SDK. It normalizes the OpenAI response shape into the
dict contract expected by every consumer of LLMProvider (i.e. a top-level
``message`` key with ``content``), which differs from raw OpenAI responses that
nest the content under ``choices[0].message``.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

from openai import OpenAI

try:  # Canonical OpenAI SDK (>=1.0) exposes exceptions under openai.exceptions
    from openai.exceptions import (
        APIError as _APIError,
        APIStatusError as _APIStatusError,
        APITimeoutError as _APITimeoutError,
        APIConnectionError as _APIConnectionError,
        AuthenticationError as _AuthenticationError,
        RateLimitError as _RateLimitError,
        OpenAIError as _OpenAIError,
    )
except ImportError:  # Some SDK variants expose exceptions at the package root
    from openai import (  # type: ignore
        APIError as _APIError,
        APIStatusError as _APIStatusError,
        APITimeoutError as _APITimeoutError,
        APIConnectionError as _APIConnectionError,
        AuthenticationError as _AuthenticationError,
        RateLimitError as _RateLimitError,
        OpenAIError as _OpenAIError,
    )
from services.backend_config.client import client as config

from .base import LLMProvider
from .exceptions import (
    LLMProviderError,
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderQuotaExceededError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)


class NVIDIAProvider(LLMProvider):
    """NVIDIA NIM provider implementation using the OpenAI-compatible SDK.

    The API key is resolved via the centralized configuration service
    (``external_apis.nvidia_api_key``) and falls back to the ``NVIDIA_API_KEY``
    environment variable so the provider can operate in local/offline dev
    setups where the backend_config service is not running.

    Default model: ``meta/muse-glimmer-30b``.
    """

    #: Default model used when no model is explicitly requested.
    DEFAULT_MODEL = "meta/muse-glimmer-30b"

    #: Base URL for the NVIDIA API (OpenAI-compatible surface).
    BASE_URL = "https://integrate.api.nvidia.com/v1"

    #: Name surfaced on the config key / exceptions as the provider identifier.
    PROVIDER_NAME = "nvidia"

    def __init__(self, timeout: float = 300.0):
        """Initialize the NVIDIA provider.

        Args:
            timeout: Per-request timeout in seconds for the OpenAI SDK client.
        """
        self.timeout = timeout
        self.api_key = self._resolve_api_key()
        import time
        import threading
        self._rate_lock = threading.Lock()
        self._rate_limiter = {"window_start": time.time(), "calls": 0}
        self._rate_limit_rpm = int(os.environ.get("NVIDIA_RATE_LIMIT_RPM", "40"))

        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=self.api_key,
            timeout=timeout,
            max_retries=0,  # deterministic: the provider does not retry on its own
        )
        logger.debug(
            "NVIDIAProvider initialized (timeout=%ss, base_url=%s)",
            self.timeout,
            self.BASE_URL,
        )

    # ------------------------------------------------------------------ #
    #  Configuration
    # ------------------------------------------------------------------ #
    def _resolve_api_key(self) -> str:
        """Resolve the NVIDIA API key from config, falling back to the env var."""
        api_key = config.get("external_apis.nvidia_api_key")
        if not api_key:
            # Fallback to environment variable (dev / offline setups).
            api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is required: set it in the backend_config "
                "service (external_apis.nvidia_api_key) or as the "
                "NVIDIA_API_KEY environment variable."
            )
        return api_key

    # ------------------------------------------------------------------ #
    #  Chat
    # ------------------------------------------------------------------ #
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get a chat completion from the NVIDIA API.

        The OpenAI response is normalized into the dict shape every consumer
        expects: ``{"message": {"role": ..., "content": ...}, ...}``.

        Args:
            model: Model name to use for completion. Falls back to
                ``DEFAULT_MODEL`` when empty.
            messages: List of message dicts with ``role`` and ``content``.
            options: Optional model-specific options. Recognized keys mirror
                the rest of the provider family: ``temperature``,
                ``num_predict`` (mapped to ``max_tokens``), ``stop`` and
                ``top_p``.

        Returns:
            Normalized response dict with a top-level ``message`` key.

        Raises:
            LLMProviderError: on API or network failure (mapped from the
                OpenAI SDK exceptions to the project's exception hierarchy).
        """
        model = model or self.DEFAULT_MODEL
        from providers.exceptions import ProviderQuotaExceededError
        import time as _time
        with self._rate_lock:
            now = _time.time()
            if now - self._rate_limiter["window_start"] >= 60:
                self._rate_limiter["window_start"] = now
                self._rate_limiter["calls"] = 0
            if self._rate_limiter["calls"] >= self._rate_limit_rpm:
                raise ProviderQuotaExceededError(
                    f"NVIDIA rate limit exceeded: {self._rate_limit_rpm} RPM",
                    provider=self.PROVIDER_NAME,
                    model=model,
                    quota_limit=str(self._rate_limit_rpm),
                )
            self._rate_limiter["calls"] += 1

        logger.debug("NVIDIAProvider.chat called with model=%s", model)

        # Build the call kwargs, mapping the project option names onto the
        # OpenAI-compatible parameter names (mirrors the OpenRouter mapping).
        kwargs: Dict[str, Any] = {"model": model, "messages": messages}
        if options:
            kwargs["temperature"] = options.get("temperature", 0.7)
            if "num_predict" in options:
                kwargs["max_tokens"] = options["num_predict"]
            if "stop" in options:
                kwargs["stop"] = options["stop"]
            if "top_p" in options:
                kwargs["top_p"] = options["top_p"]

        start_time = time.time()
        try:
            completion = self.client.chat.completions.create(**kwargs)
        except _APITimeoutError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA timeout after %.3fs: %s", duration, e)
            raise ProviderTimeoutError(
                f"NVIDIA timeout: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
                timeout_seconds=self.timeout,
            ) from e
        except _RateLimitError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA rate limit after %.3fs: %s", duration, e)
            raise ProviderQuotaExceededError(
                f"NVIDIA quota exceeded: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
                quota_limit=_error_details_from(e),
            ) from e
        except _AuthenticationError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA auth failure after %.3fs: %s", duration, e)
            raise ProviderAuthenticationError(
                f"NVIDIA authentication failed: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
                auth_error=str(e),
            ) from e
        except _APIConnectionError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA connection error after %.3fs: %s", duration, e)
            raise ProviderConnectionError(
                f"NVIDIA connection error: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
                connection_error=str(e),
            ) from e
        except _APIStatusError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA API error after %.3fs: %s", duration, e)
            raise ProviderAPIError(
                f"NVIDIA API error: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
                status_code=_status_code_from(e),
                error_details=_error_details_from(e),
            ) from e
        except _APIError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA API error after %.3fs: %s", duration, e)
            raise LLMProviderError(
                f"NVIDIA API error: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
            ) from e
        except _OpenAIError as e:
            duration = time.time() - start_time
            logger.error("NVIDIA SDK error after %.3fs: %s", duration, e)
            raise LLMProviderError(
                f"NVIDIA request failed: {e}",
                provider=self.PROVIDER_NAME,
                model=model,
            ) from e

        duration = time.time() - start_time

        # Normalize the OpenAI response into the dict shape every consumer in
        # this project expects (top-level ``message`` with ``content``).
        response = self._normalize_completion(completion)

        logger.debug("NVIDIA chat request: %s", json.dumps(kwargs, ensure_ascii=False))
        logger.debug("NVIDIA chat response: %s", json.dumps(response, ensure_ascii=False))
        self._log_inference(self.PROVIDER_NAME, model, messages, response, duration)

        return response

    def _normalize_completion(self, completion: Any) -> Dict[str, Any]:
        """Convert an OpenAI ``ChatCompletion`` into the normalized dict shape."""
        choices = getattr(completion, "choices", []) or []
        message = {"role": "assistant", "content": ""}
        if choices:
            first = getattr(choices[0], "message", None)
            if first is not None:
                message = {
                    "role": getattr(first, "role", None) or "assistant",
                    "content": getattr(first, "content", None) or "",
                }

        usage = getattr(completion, "usage", None)
        usage_dict = None
        if usage is not None:
            usage_dict = _to_dict(usage)

        return {
            "id": getattr(completion, "id", None),
            "model": getattr(completion, "model", None),
            "object": getattr(completion, "object", "chat.completion"),
            "created": getattr(completion, "created", None),
            "message": message,
            "choices": [_choice_to_dict(c) for c in choices],
            "usage": usage_dict,
        }

    # ------------------------------------------------------------------ #
    #  Embeddings (stubs)
    # ------------------------------------------------------------------ #
    def embed(self, model: str, text: str) -> List[float]:
        """Get embedding vector for a single text.

        Stub: NVIDIA's NIM embeddings endpoint is model-specific and not wired
        to the default chat model. Consumers should use a dedicated embedding
        provider (e.g. Ollama ``mxbai-embed-large``).
        """
        logger.warning("NVIDIA embed stub called for model=%s", model)
        raise NotImplementedError(
            "NVIDIAProvider does not yet implement embeddings. "
            "Use a dedicated embedding provider (e.g. Ollama mxbai-embed-large)."
        )

    def embed_batch(self, model: str, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts.

        Stub: delegates to :meth:`embed` semantics; not implemented yet.
        """
        logger.warning("NVIDIA embed_batch stub called for model=%s (%d texts)", model, len(texts))
        raise NotImplementedError(
            "NVIDIAProvider does not yet implement embeddings. "
            "Use a dedicated embedding provider (e.g. Ollama mxbai-embed-large)."
        )

    # ------------------------------------------------------------------ #
    #  Model management (stubs)
    # ------------------------------------------------------------------ #
    def list_model_names(self) -> Set[str]:
        """Return known model names from the provider.

        Stub: returns the configured default model only. A real implementation
        would call ``GET /v1/models`` against the NVIDIA API.
        """
        logger.debug("NVIDIAProvider.list_model_names stub called")
        return {self.DEFAULT_MODEL}

    def pull_model(self, model_name: str) -> None:
        """Pull/preload a model into the provider.

        Stub: the NVIDIA API is a cloud service; models are not pre-pulled.
        """
        logger.debug("NVIDIAProvider.pull_model stub called with model_name=%s", model_name)
        # No-op: cloud-hosted models do not require pulling.
        return None


# ----------------------------------------------------------------------
#  Helpers (module-level so they work without an instance)
# ----------------------------------------------------------------------
def _status_code_from(exc: Any) -> Optional[int]:
    """Best-effort extraction of an HTTP status code from an OpenAI error."""
    code = getattr(exc, "status_code", None)
    if code is not None:
        return int(code)
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            return int(response.status_code)
        except Exception:
            return None
    return None


def _error_details_from(exc: Any) -> Optional[str]:
    """Best-effort extraction of human-readable error details from an OpenAI error."""
    body = getattr(exc, "body", None)
    if body is not None:
        try:
            return json.dumps(body, ensure_ascii=False, default=str)
        except Exception:
            return str(body)
    return str(exc)


def _to_dict(obj: Any) -> Any:
    """Convert a Pydantic model (or anything) to a plain JSON-able dict."""
    if obj is None:
        return None
    # Prefer pydantic-style serialization when available.
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump()
        except Exception:
            pass
    dict_ = getattr(obj, "dict", None)
    if callable(dict_):
        try:
            return dict_()
        except Exception:
            pass
    return obj


def _choice_to_dict(choice: Any) -> Dict[str, Any]:
    """Flatten a Choice's message into the dict shape for the normalized response."""
    message = getattr(choice, "message", None)
    content = getattr(message, "content", None) if message is not None else None
    role = getattr(message, "role", None) if message is not None else None
    return {
        "index": getattr(choice, "index", 0),
        "message": {"role": role or "assistant", "content": content or ""},
        "finish_reason": getattr(choice, "finish_reason", None),
    }
