from fastapi import APIRouter, FastAPI
from .scheme import CompletionRequest
from .service import (
    ChatService,
    InfoService,
    LoadModelsService,
    resolve_keep_alive,
)
from contextlib import asynccontextmanager
import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Initialization
# -------------------------------------------------
info_service: InfoService | None = None


def _prefer_gpu_enabled() -> bool:
    raw = os.getenv("AGENTS_OLLAMA_PREFER_GPU", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _detect_gpu_available() -> bool:
    nvidia_visible = os.getenv("NVIDIA_VISIBLE_DEVICES", "").strip()
    if nvidia_visible and nvidia_visible.lower() not in {"none", "void"}:
        return True

    if shutil.which("nvidia-smi") is None:
        return False

    try:
        completed = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return completed.returncode == 0 and bool(completed.stdout.strip())
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global info_service
    keep_alive = resolve_keep_alive()
    gpu_requested = _prefer_gpu_enabled()
    gpu_detected = _detect_gpu_available()
    logger.info(
        "[ollama-runtime] startup keep_alive=%s gpu_requested=%s gpu_detected=%s",
        keep_alive,
        gpu_requested,
        gpu_detected,
    )
    if gpu_requested and not gpu_detected:
        logger.warning(
            "[ollama-runtime] GPU requested but not detected. Falling back to CPU."
        )

    load_models_service = LoadModelsService()
    load_models_service.download_models()
    info_service = InfoService()
    yield


router = APIRouter()


@router.post("/completions")
def get_completions(request: CompletionRequest):
    response = ChatService().chat(request)
    return response


@router.get("/info")
def get_info():
    return info_service.get_info()


@router.get("/health")
def health_check():
    return {"status": "ok"}
