import logging
import os
import threading
import time
from typing import Any, Dict, List

import ollama

from .scheme import CompletionRequest

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


_OLLAMA_MODEL_LOCK = threading.Lock()
_DEFAULT_KEEP_ALIVE = "0s"


def resolve_keep_alive() -> str:
    raw = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", _DEFAULT_KEEP_ALIVE).strip()
    return raw if raw else _DEFAULT_KEEP_ALIVE


def _ollama_chat_with_runtime(*, model: str, messages: List[Dict[str, Any]], **kwargs):
    keep_alive = resolve_keep_alive()
    start = time.perf_counter()
    logger.info(
        "[ollama-runtime] waiting_lock model=%s keep_alive=%s",
        model,
        keep_alive,
    )
    with _OLLAMA_MODEL_LOCK:
        logger.info(
            "[ollama-runtime] lock_acquired model=%s keep_alive=%s",
            model,
            keep_alive,
        )
        response = ollama.chat(
            model=model,
            messages=messages,
            keep_alive=keep_alive,
            **kwargs,
        )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "[ollama-runtime] lock_released model=%s elapsed_ms=%s keep_alive=%s",
        model,
        elapsed_ms,
        keep_alive,
    )
    return response


class LoadModelsService:
    def __init__(
        self,
        names: list = None,
    ):
        if names is None:
            self.names = [
                "yasserrmd/Qwen2.5-7B-Instruct-1M",
                "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
                "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M",
            ]
        else:
            self.names = names

    def download_models(self):
        installed_models = []
        max_retries = 5
        for _ in range(max_retries):
            try:
                response = ollama.list()
                installed_models = {m["name"] for m in response.get("models", [])}
                break
            except Exception:
                time.sleep(2)

        for model_name in self.names:
            if model_name in installed_models:
                logger.info("Model already available (skip): %s", model_name)
                continue
            logger.info("Downloading missing model: %s", model_name)
            try:
                ollama.pull(model_name)
                logger.info("Model downloaded: %s", model_name)
            except Exception as exc:
                logger.info("Error downloading model %s: %s", model_name, exc)


class ChatService:
    def __init__(self, name: str = "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"):
        self.name = name

    def chat(self, request: CompletionRequest) -> Dict[str, Any]:
        options = {
            "temperature": (
                request.temperature if request.temperature is not None else 0.7
            ),
            "num_predict": (
                request.max_tokens if request.max_tokens is not None else 512
            ),
        }
        try:
            response = _ollama_chat_with_runtime(
                model=self.name,
                messages=request.history,
                options=options,
            )
            return response["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"Chat model invocation failed: {exc}") from exc


class CifService:
    def __init__(self, name: str = "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M"):
        self.name = name

    def get_cif(self, compound_name: str, max_tokens: int = 512) -> str:
        prompt = (
            "Provide the CIF file content for the compound: "
            f"{compound_name}. Only return the CIF content without any additional text."
        )
        messages = [{"role": "user", "content": prompt}]
        options = {
            "temperature": 0.0,
            "num_predict": max_tokens,
        }
        try:
            response = _ollama_chat_with_runtime(
                model=self.name,
                messages=messages,
                options=options,
            )
            return response["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"CIF retrieval failed: {exc}") from exc


class InfoService:
    def __init__(self):
        pass

    def get_info(self):
        payload = {}
        payload["service"] = "agent_policy_ollama"
        payload["ChatService"] = {
            "Model": "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
            "Version": "1.0.0",
        }
        payload["policy_version"] = "removed_from_runtime"
        return payload
