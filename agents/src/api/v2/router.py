import logging
import os
import shutil
import subprocess
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException

from .models import build_models
from .routes_embeddings import router as embeddings_router
from .scheme import (
    CompletionRequest,
    CifRequest,
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
)
from .service import V2RuntimeServices, resolve_keep_alive

logger = logging.getLogger(__name__)

router = APIRouter()
_decision_model, _evaluator_model = build_models()
router.include_router(embeddings_router)
runtime_services: V2RuntimeServices | None = None


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
    del app
    global runtime_services

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

    runtime_services = V2RuntimeServices(keep_alive=keep_alive)
    runtime_services.loader.download_models()
    yield


@router.post("/decision", response_model=DecisionModelOutput)
def decision(payload: DecisionModelInput):
    try:
        result = _decision_model.call(payload)
        return result
    except Exception as exc:
        logger.exception("decision_model call failed")
        raise HTTPException(
            status_code=503, detail=f"decision_model_failed: {exc}"
        ) from exc


@router.post("/evaluate", response_model=EvaluatorModelOutput)
def evaluate(payload: EvaluatorModelInput):
    try:
        result = _evaluator_model.call(payload)
        return result
    except Exception as exc:
        logger.exception("evaluator_model call failed")
        raise HTTPException(
            status_code=503, detail=f"evaluator_model_failed: {exc}"
        ) from exc


@router.post("/completions")
def get_completions(request: CompletionRequest):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        return runtime_services.chat.chat(
            history=request.history,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"chat_failed: {exc}") from exc


@router.get("/info")
def get_info():
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    return runtime_services.info.get_info()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/cif")
def get_cif(request: CifRequest):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        cif = runtime_services.cif.get_cif(
            compound_name=request.compound_name,
            max_tokens=request.max_tokens,
        )
        return {"cif": cif}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"cif_failed: {exc}") from exc
