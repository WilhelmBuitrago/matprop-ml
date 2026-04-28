import logging
import os
import shutil
import subprocess
import time
from contextlib import asynccontextmanager
from typing import Any, List, Dict

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .scheme import (
    CompletionRequest,
    CifRequest,
    CrystalCompletionRequest,
    CrystalSpecExtractionRequest,
    DecisionModelInput,
    DecisionModelOutput,
    DomainCriticRequest,
    DomainCriticResponse,
    InsightRequest,
    InsightResponse,
    PlanningEvaluatorOutput,
    PlanningEvaluatorRequest,
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


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048


class ProviderConfig(BaseModel):
    """Configuration for model providers."""
    models: Dict[str, ModelConfig]
    fallback_chain: List[str]


class ConfigResponse(BaseModel):
    """Response model for configuration endpoint."""
    config: ProviderConfig


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration update."""
    models: Dict[str, ModelConfig]
    fallback_chain: List[str]


def _prefer_gpu_enabled() -> bool:
    """
    Check if GPU preference is enabled via environment variable.
    
    Returns:
        bool: True if GPU is preferred, False otherwise
    """
    raw = os.getenv("AGENTS_OLLAMA_PREFER_GPU", "true").strip().lower()
    enabled = raw not in {"0", "false", "no", "off"}
    logger.debug("GPU preference: %s (raw=%s)", enabled, raw)
    return enabled


def _detect_gpu_available() -> bool:
    """
    Detect if GPU is available for Ollama runtime.
    
    Returns:
        bool: True if GPU is detected, False otherwise
    """
    nvidia_visible = os.getenv("NVIDIA_VISIBLE_DEVICES", "").strip()
    if nvidia_visible and nvidia_visible.lower() not in {"none", "void"}:
        logger.info("GPU detected via NVIDIA_VISIBLE_DEVICES: %s", nvidia_visible)
        return True

    if shutil.which("nvidia-smi") is None:
        logger.debug("nvidia-smi not found, assuming no GPU")
        return False

    try:
        completed = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        available = completed.returncode == 0 and bool(completed.stdout.strip())
        logger.info("GPU detection via nvidia-smi: %s", available)
        return available
    except Exception as e:
        logger.warning("GPU detection failed: %s", e, exc_info=True)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for Ollama services.
    
    Args:
        app: FastAPI application instance
    """
    del app
    global runtime_services

    start_time = time.time()
    logger.info("[LIFESPAN] Starting runtime services initialization")
    
    keep_alive = resolve_keep_alive()
    gpu_requested = _prefer_gpu_enabled()
    gpu_detected = _detect_gpu_available()
    logger.info(
        "[LIFESPAN] Configuration: keep_alive=%s gpu_requested=%s gpu_detected=%s",
        keep_alive,
        gpu_requested,
        gpu_detected,
    )
    if gpu_requested and not gpu_detected:
        logger.warning(
            "[LIFESPAN] GPU requested but not detected. Falling back to CPU."
        )

    runtime_services = V2RuntimeServices(keep_alive=keep_alive)
    logger.info("[LIFESPAN] Downloading required models...")
    runtime_services.download_models()
    
    init_duration = time.time() - start_time
    logger.info("[LIFESPAN] Initialization completed in %.2f seconds", init_duration)
    yield
    
    logger.info("[LIFESPAN] Shutdown completed")


@router.post("/decision", response_model=DecisionModelOutput)
def decision(request: Request, payload: DecisionModelInput) -> DecisionModelOutput:
    """
    Execute decision model to select next action for materials-agent loop.
    
    Args:
        request: FastAPI request object
        payload: Decision model input containing query, intent, state, and available tools
    
    Returns:
        Decision model output with selected action and confidence
    """
    if runtime_services is None:
        logger.error("[DECISION] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[DECISION] Request received | client=%s | query_len=%d | tools_count=%d",
        request.client.host if request.client else "unknown",
        len(payload.query),
        len(payload.tools_available),
    )
    
    try:
        result = runtime_services.decision.call(payload)
        duration = time.time() - request_start
        logger.info(
            "[DECISION] Success | duration=%.3fs | action=%s | confidence=%.2f",
            duration,
            result.action,
            result.confidence,
        )
        return result
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[DECISION] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(
            status_code=503, detail=f"decision_model_failed: {exc}"
        ) from exc


@router.post("/planning-evaluator", response_model=PlanningEvaluatorOutput)
def planning_evaluator(request: Request, payload: PlanningEvaluatorRequest) -> PlanningEvaluatorOutput:
    """
    Execute planning or evaluation for materials-agent pipeline.
    
    Args:
        request: FastAPI request object
        payload: Planning/evaluation request containing mode and context
    
    Returns:
        Planning/evaluation output with steps or feedback
    """
    if runtime_services is None:
        logger.error("[PLANNING-EVALUATOR] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[PLANNING-EVALUATOR] Request received | client=%s | mode=%s | query_len=%d",
        request.client.host if request.client else "unknown",
        payload.mode,
        len(payload.query),
    )
    
    try:
        result = runtime_services.planning_evaluator.call(payload)
        duration = time.time() - request_start
        logger.info(
            "[PLANNING-EVALUATOR] Success | duration=%.3fs | steps_count=%d | feedback_len=%d",
            duration,
            len(result.steps),
            len(result.feedback),
        )
        return result
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[PLANNING-EVALUATOR] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(
            status_code=503, detail=f"planning_evaluator_failed: {exc}"
        ) from exc


@router.post("/domain-critic", response_model=DomainCriticResponse)
def domain_critic(request: Request, payload: DomainCriticRequest) -> DomainCriticResponse:
    """
    Execute domain critic evaluation for response validation.
    
    Args:
        request: FastAPI request object
        payload: Domain critic request containing user query and draft response
    
    Returns:
        Domain critic response with validation feedback
    """
    if runtime_services is None:
        logger.error("[DOMAIN-CRITIC] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[DOMAIN-CRITIC] Request received | client=%s | query_len=%d | reasoning_steps=%d",
        request.client.host if request.client else "unknown",
        len(payload.user_query),
        len(payload.reasoning_steps),
    )
    
    try:
        result = runtime_services.domain_critic.call(payload)
        duration = time.time() - request_start
        logger.info(
            "[DOMAIN-CRITIC] Success | duration=%.3fs | response_len=%d",
            duration,
            len(result.response),
        )
        return result
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[DOMAIN-CRITIC] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(
            status_code=503, detail=f"domain_critic_failed: {exc}"
        ) from exc


@router.post("/completions")
def get_completions(request: Request, request_data: CompletionRequest) -> str:
    """
    Generate chat completions using the chat service.
    
    Args:
        request: FastAPI request object
        request_data: Completion request containing conversation history
    
    Returns:
        Generated completion text
    """
    if runtime_services is None:
        logger.error("[COMPLETIONS] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[COMPLETIONS] Request received | client=%s | history_len=%d | model=%s",
        request.client.host if request.client else "unknown",
        len(request_data.history),
        request_data.model_name or "default",
    )
    
    try:
        result = runtime_services.chat.chat(
            history=request_data.history,
            temperature=request_data.temperature,
            max_tokens=request_data.max_tokens,
            model_name=request_data.model_name,
            stop_tokens=request_data.stop_tokens,
        )
        duration = time.time() - request_start
        logger.info(
            "[COMPLETIONS] Success | duration=%.3fs | response_len=%d",
            duration,
            len(result),
        )
        return result
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[COMPLETIONS] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(status_code=503, detail=f"chat_failed: {exc}") from exc


@router.post("/crystal/spec")
def extract_crystal_spec(request: Request, request_data: CrystalSpecExtractionRequest) -> dict[str, Any]:
    """
    Extract crystal structure specification from query.
    
    Args:
        request: FastAPI request object
        request_data: Crystal spec extraction request
    
    Returns:
        Dict containing extracted specification
    """
    if runtime_services is None:
        logger.error("[CRYSTAL-SPEC] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[CRYSTAL-SPEC] Request received | client=%s | query_len=%d",
        request.client.host if request.client else "unknown",
        len(request_data.query),
    )
    
    try:
        parsed = runtime_services.crystal_spec.extract(
            query=request_data.query,
            deterministic_spec=request_data.deterministic_spec,
        )
        duration = time.time() - request_start
        logger.info(
            "[CRYSTAL-SPEC] Success | duration=%.3fs",
            duration,
        )
        return {"spec": parsed}
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[CRYSTAL-SPEC] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(
            status_code=503, detail=f"crystal_spec_failed: {exc}"
        ) from exc


@router.post("/crystal/complete")
def complete_crystal(request: Request, request_data: CrystalCompletionRequest) -> dict[str, str]:
    """
    Generate crystal structure completion from prompt.
    
    Args:
        request: FastAPI request object
        request_data: Crystal completion request
    
    Returns:
        Dict containing generated text
    """
    if runtime_services is None:
        logger.error("[CRYSTAL-COMPLETE] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[CRYSTAL-COMPLETE] Request received | client=%s | model=%s",
        request.client.host if request.client else "unknown",
        request_data.model_name or "default",
    )
    
    try:
        text = runtime_services.cif.generate_from_prompt(
            system_message=request_data.system_message,
            user_prompt=request_data.user_prompt,
            temperature=request_data.temperature,
            max_tokens=request_data.max_tokens,
            model_name=request_data.model_name,
            stop_tokens=request_data.stop_tokens,
        )
        duration = time.time() - request_start
        logger.info(
            "[CRYSTAL-COMPLETE] Success | duration=%.3fs | response_len=%d",
            duration,
            len(text),
        )
        return {"raw_generation": text}
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[CRYSTAL-COMPLETE] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(
            status_code=503, detail=f"crystal_complete_failed: {exc}"
        ) from exc


@router.get("/info")
def get_info(request: Request) -> dict[str, Any]:
    """
    Get service information and configuration.
    
    Args:
        request: FastAPI request object
    
    Returns:
        Dict containing service info
    """
    if runtime_services is None:
        logger.error("[INFO] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    logger.info(
        "[INFO] Request received | client=%s",
        request.client.host if request.client else "unknown",
    )
    return runtime_services.info.get_info()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    logger.debug("[HEALTH] Health check requested")
    return {"status": "ok"}


@router.post("/cif")
def get_cif(request: Request, request_data: CifRequest) -> dict[str, str]:
    """
    Generate CIF file content for a compound.
    
    Args:
        request: FastAPI request object
        request_data: CIF request containing compound name
    
    Returns:
        Dict containing CIF content
    """
    if runtime_services is None:
        logger.error("[CIF] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[CIF] Request received | client=%s | compound=%s",
        request.client.host if request.client else "unknown",
        request_data.compound_name,
    )
    
    try:
        cif = runtime_services.cif.get_cif(
            compound_name=request_data.compound_name,
            max_tokens=request_data.max_tokens,
        )
        duration = time.time() - request_start
        logger.info(
            "[CIF] Success | duration=%.3fs | response_len=%d",
            duration,
            len(cif),
        )
        return {"cif": cif}
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[CIF] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(status_code=503, detail=f"cif_failed: {exc}") from exc


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embed_texts(request: Request, request_data: EmbeddingRequest) -> EmbeddingResponse:
    """
    Generate embeddings for multiple texts.
    
    Args:
        request: FastAPI request object
        request_data: Embedding request containing texts to embed
    
    Returns:
        Embedding response with vectors
    """
    if runtime_services is None:
        logger.error("[EMBEDDINGS] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    if not request_data.texts:
        logger.warning("[EMBEDDINGS] Empty texts list received from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=400, detail="texts list cannot be empty")
    
    request_start = time.time()
    logger.info(
        "[EMBEDDINGS] Request received | client=%s | text_count=%d",
        request.client.host if request.client else "unknown",
        len(request_data.texts),
    )
    
    try:
        embeddings = runtime_services.embeddings.embed_texts(request_data.texts)
        duration = time.time() - request_start
        logger.info(
            "[EMBEDDINGS] Success | duration=%.3fs | text_count=%d | embedding_dim=%d",
            duration,
            len(request_data.texts),
            len(embeddings[0]) if embeddings else 0,
        )
        return EmbeddingResponse(embeddings=embeddings)
    except RuntimeError as exc:
        duration = time.time() - request_start
        logger.error("[EMBEDDINGS] Runtime error | duration=%.3fs | error=%s", duration, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding service failed: {exc}",
        ) from exc
    except Exception as exc:
        duration = time.time() - request_start
        logger.error("[EMBEDDINGS] Unexpected error | duration=%.3fs | error=%s", duration, exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/insights", response_model=InsightResponse)
def extract_insights(request: Request, request_data: InsightRequest) -> InsightResponse:
    """
    Extract insights from document chunk.
    
    Args:
        request: FastAPI request object
        request_data: Insight extraction request
    
    Returns:
        Insight response with extracted facts
    """
    if runtime_services is None:
        logger.error("[INSIGHTS] Runtime services unavailable")
        raise HTTPException(status_code=503, detail="runtime_services_unavailable")
    
    request_start = time.time()
    logger.info(
        "[INSIGHTS] Request received | client=%s | query_len=%d | chunk_len=%d",
        request.client.host if request.client else "unknown",
        len(request_data.query),
        len(request_data.chunk),
    )
    
    try:
        insights = runtime_services.insights.extract_insights(
            query=request_data.query,
            title=request_data.title,
            section=request_data.section,
            page=request_data.page,
            chunk=request_data.chunk,
            max_tokens=request_data.max_tokens,
        )
        duration = time.time() - request_start
        logger.info(
            "[INSIGHTS] Success | duration=%.3fs | insights_count=%d",
            duration,
            len(insights),
        )
        return InsightResponse(insights=insights)
    except Exception as exc:
        duration = time.time() - request_start
        logger.exception(
            "[INSIGHTS] Failed | duration=%.3fs | error=%s",
            duration,
            str(exc),
        )
        raise HTTPException(status_code=503, detail=f"insights_failed: {exc}") from exc


@router.get("/config", response_model=ConfigResponse)
def get_config(request: Request) -> ConfigResponse:
    """
    Get current provider and model configuration.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current configuration
    """
    logger.info("[CONFIG] Get config request received | client=%s", 
               request.client.host if request.client else "unknown")
    
    # Get current environment variables for model configurations
    config_data = {
        "models": {
            "evaluator": {
                "provider": os.getenv("AGENT_EVALUATOR_PROVIDER", "ollama"),
                "model": os.getenv("AGENT_EVALUATOR_MODEL", "deepseek-r1:8b"),
                "temperature": float(os.getenv("AGENT_EVALUATOR_TEMPERATURE", 0.7)),
                "max_tokens": int(os.getenv("AGENT_EVALUATOR_MAX_TOKENS", 2048))
            },
            "planner": {
                "provider": os.getenv("AGENT_PLANNER_PROVIDER", "ollama"),
                "model": os.getenv("AGENT_PLANNER_MODEL", "deepseek-r1:8b"),
                "temperature": float(os.getenv("AGENT_PLANNER_TEMPERATURE", 0.7)),
                "max_tokens": int(os.getenv("AGENT_PLANNER_MAX_TOKENS", 2048))
            },
            "domain_critic": {
                "provider": os.getenv("AGENT_DOMAIN_CRITIC_PROVIDER", "openrouter"),
                "model": os.getenv("AGENT_DOMAIN_CRITIC_MODEL", "meta-llama/llama-3.1-70b-instruct:free"),
                "temperature": float(os.getenv("AGENT_DOMAIN_CRITIC_TEMPERATURE", 0.7)),
                "max_tokens": int(os.getenv("AGENT_DOMAIN_CRITIC_MAX_TOKENS", 2048))
            }
        },
        "fallback_chain": os.getenv("AGENT_FALLBACK_CHAIN", "ollama,openrouter").split(",")
    }
    
    return ConfigResponse(config=ProviderConfig(**config_data))


@router.post("/config")
def update_config(request: Request, config_data: ConfigUpdateRequest) -> dict:
    """
    Update provider and model configuration.
    
    Args:
        request: FastAPI request object
        config_data: New configuration data
        
    Returns:
        Status of configuration update
    """
    logger.info("[CONFIG] Update config request received | client=%s", 
               request.client.host if request.client else "unknown")
    
    try:
        # Update environment variables for model configurations
        for model_name, model_config in config_data.models.items():
            # Set environment variables for each model configuration
            provider_key = f"AGENT_{model_name.upper()}_PROVIDER"
            model_key = f"AGENT_{model_name.upper()}_MODEL"
            
            os.environ[provider_key] = model_config.provider
            os.environ[model_key] = model_config.model
            
            # For each model type, update the specific configuration
            if model_name == "evaluator":
                os.environ["AGENT_EVALUATOR_PROVIDER"] = model_config.provider
                os.environ["AGENT_EVALUATOR_MODEL"] = model_config.model
            elif model_name == "planner":
                os.environ["AGENT_PLANNER_PROVIDER"] = model_config.provider
                os.environ["AGENT_PLANNER_MODEL"] = model_config.model
            elif model_name == "domain_critic":
                os.environ["AGENT_DOMAIN_CRITIC_PROVIDER"] = model_config.provider
                os.environ["AGENT_DOMAIN_CRITIC_MODEL"] = model_config.model
        
        # Update fallback chain
        if config_data.fallback_chain:
            os.environ["AGENT_FALLBACK_CHAIN"] = ",".join(config_data.fallback_chain)
        
        logger.info("[CONFIG] Configuration updated successfully")
        return {"status": "success", "message": "Configuration updated successfully"}
        
    except Exception as exc:
        logger.error("[CONFIG] Failed to update configuration: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {exc}")
