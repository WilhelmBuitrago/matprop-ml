"""Model lifecycle services for Ollama-backed models."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from models import ALL_MODELS
from .ollama_client import OllamaClient
from providers.factory import _parse_provider_model

logger = logging.getLogger(__name__)

# Whitelist of Ollama models to download/verify at startup
_OLLAMA_WHITELIST = {
    "mxbai-embed-large",
    "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M",
    "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
}


class LoadModelsService:
    """Ensure required models are available in the local Ollama runtime."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        names: Iterable[str] | None = None,
    ) -> None:
        self._client = ollama_client
        raw_names = list(names) if names is not None else list(ALL_MODELS)
        # Normalize, filter to Ollama provider and whitelist, strip provider prefix
        filtered: list[str] = []
        for raw in raw_names:
            provider, model = _parse_provider_model(raw)
            if provider.lower() not in ("ollama", "llamat"):
                logger.info("Skipping non-Ollama model: %s", raw)
                continue
            if not model:
                logger.info("Skipping empty model name for %s", raw)
                continue
            if model not in _OLLAMA_WHITELIST:
                # Model not in whitelist - skip download
                continue
            if model not in filtered:
                filtered.append(model)
        self.names = filtered

    def download_models(self) -> None:
        installed_models: set[str] = set()
        max_retries = 5
        for _ in range(max_retries):
            try:
                installed_models = self._client.list_model_names()
                break
            except Exception:
                time.sleep(2)

        checked = 0
        downloaded = 0
        failed = 0
        skipped = 0

        for model_name in self.names:
            checked += 1
            if model_name in installed_models:
                logger.info("Model already available (skip): %s", model_name)
                skipped += 1
                continue
            logger.info("Downloading missing model: %s", model_name)
            try:
                self._client.pull_model(model_name)
                logger.info("Model downloaded: %s", model_name)
                downloaded += 1
            except Exception as exc:
                logger.warning("Failed to pull model %s: %s", model_name, exc)
                failed += 1

        logger.info(
            "Model download complete: checked=%d, downloaded=%d, skipped=%d, failed=%d",
            checked,
            downloaded,
            skipped,
            failed,
        )
