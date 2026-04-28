"""Model lifecycle services for Ollama-backed models."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from models import ALL_MODELS
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class LoadModelsService:
    """Ensure required models are available in the local Ollama runtime."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        names: Iterable[str] | None = None,
    ) -> None:
        self._client = ollama_client
        self.names = list(names) if names is not None else list(ALL_MODELS)

    def download_models(self) -> None:
        installed_models: set[str] = set()
        max_retries = 5
        for _ in range(max_retries):
            try:
                installed_models = self._client.list_model_names()
                break
            except Exception:
                time.sleep(2)

        for model_name in self.names:
            if model_name in installed_models:
                logger.info("Model already available (skip): %s", model_name)
                continue
            logger.info("Downloading missing model: %s", model_name)
            try:
                self._client.pull_model(model_name)
                logger.info("Model downloaded: %s", model_name)
            except Exception as exc:
                logger.info("Error downloading model %s: %s", model_name, exc)
