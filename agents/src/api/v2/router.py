import logging
import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .scheme import (
    CompletionRequest,
    CifRequest,
    CrystalCompletionRequest,
    CrystalSpecExtractionRequest,
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
    InsightRequest,
    InsightResponse,
    PlannerRequest,
    PlannerResponse,
)
from .service import V2RuntimeServices, resolve_keep_alive

logger = logging.getLogger(__name__)

router = APIRouter()
runtime_services: V2RuntimeServices | None = None


class EmbeddingRequest(BaseModel):
    """Request body for embeddings endpoint."""

    texts: List[str] = Field(..., min_items=1, description="List of texts to embed")


class EmbeddingResponse(BaseModel):
    """Response body for embeddings endpoint."""

    embeddings: List[List[float]] = Field(..., description="Embedding vectors")


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
    runtime_services.download_models()
    yield


@router.post("/decision", response_model=DecisionModelOutput)
def decision(payload: DecisionModelInput):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        result = runtime_services.decision.call(payload)
        return result
    except Exception as exc:
        logger.exception("decision_model call failed")
        raise HTTPException(
            status_code=503, detail=f"decision_model_failed: {exc}"
        ) from exc


@router.post("/evaluate", response_model=EvaluatorModelOutput)
def evaluate(payload: EvaluatorModelInput):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        result = runtime_services.evaluator.call(payload)
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
            model_name=request.model_name,
            stop_tokens=request.stop_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"chat_failed: {exc}") from exc


@router.post("/crystal/spec")
def extract_crystal_spec(request: CrystalSpecExtractionRequest):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        parsed = runtime_services.crystal_spec.extract(
            query=request.query,
            deterministic_spec=request.deterministic_spec,
        )
        return {"spec": parsed}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"crystal_spec_failed: {exc}"
        ) from exc


@router.post("/crystal/complete")
def complete_crystal(request: CrystalCompletionRequest):
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    try:
        text = runtime_services.cif.generate_from_prompt(
            system_message=request.system_message,
            user_prompt=request.user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model_name=request.model_name,
            stop_tokens=request.stop_tokens,
        )
        return {"raw_generation": text}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"crystal_complete_failed: {exc}"
        ) from exc


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


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embed_texts(request: EmbeddingRequest) -> EmbeddingResponse:
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    try:
        embeddings = runtime_services.embeddings.embed_texts(request.texts)
        return EmbeddingResponse(embeddings=embeddings)
    except RuntimeError as exc:
        logger.error("Embedding failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding service failed: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected embeddings error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/insights", response_model=InsightResponse)
def extract_insights(request: InsightRequest) -> InsightResponse:
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")

    try:
        insights = runtime_services.insights.extract_insights(
            query=request.query,
            title=request.title,
            section=request.section,
            page=request.page,
            chunk=request.chunk,
            max_tokens=request.max_tokens,
        )
        return InsightResponse(insights=insights)
    except Exception as exc:
        logger.exception("insights extraction failed")
        raise HTTPException(status_code=503, detail=f"insights_failed: {exc}") from exc


@router.post("/planner", response_model=PlannerResponse)
def planner(request: PlannerRequest) -> PlannerResponse:
    if runtime_services is None:
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")

    try:
        result = runtime_services.planner.build_plan(
            query=request.query,
            state=request.state,
            candidate_tools=[tool.model_dump() for tool in request.candidate_tools],
            max_steps=request.max_steps,
        )
        return PlannerResponse.model_validate(result)
    except Exception as exc:
        logger.exception("planner failed")
        raise HTTPException(status_code=503, detail=f"planner_failed: {exc}") from exc
