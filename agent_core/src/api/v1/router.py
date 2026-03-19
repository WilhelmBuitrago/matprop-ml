from fastapi import APIRouter, FastAPI
from .scheme import Tools, CompletionRequest
from tools.config import get_available_tools_for_runtime
from .service import CompletionService
from contextlib import asynccontextmanager
import requests
import os
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

router = APIRouter()
logger = logging.getLogger(__name__)

BACKEND_LLM_URL = os.getenv("BACKEND_LLM_URL", "http://backend-llm:8001")
HTTP_TIMEOUT_SECONDS = int(os.getenv("INTERNAL_HTTP_TIMEOUT_SECONDS", "20"))

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET", "POST"),
)
adapter = HTTPAdapter(max_retries=retry)
http = requests.Session()
http.mount("http://", adapter)
http.mount("https://", adapter)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_service
    chat_service = CompletionService()
    yield


@router.get("/tools", response_model=Tools)
def get_tools():
    return {"tools": get_available_tools_for_runtime()}


@router.post("/completions")
def chat(request: CompletionRequest):
    response = chat_service.chat(request)
    return response


@router.get("/historial_summary")
def historial_summary_endpoint():
    response = http.get(
        f"{BACKEND_LLM_URL}/v1/historial_summary", timeout=HTTP_TIMEOUT_SECONDS
    )
    return response.json()


@router.post("/clear_history")
def clear_history_endpoint():
    response = http.post(
        f"{BACKEND_LLM_URL}/v1/clear_history", timeout=HTTP_TIMEOUT_SECONDS
    )
    return response.json()


@router.get("/clear_history")
def clear_history_endpoint_deprecated():
    logger.warning("GET /v1/clear_history is deprecated. Use POST /v1/clear_history")
    response = http.post(
        f"{BACKEND_LLM_URL}/v1/clear_history", timeout=HTTP_TIMEOUT_SECONDS
    )
    return response.json()


@router.get("/conversation_history")
def conversation_history_endpoint():
    response = http.get(
        f"{BACKEND_LLM_URL}/v1/conversation_history", timeout=HTTP_TIMEOUT_SECONDS
    )
    return response.json()


@router.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    print(AVAILABLES_TOOLS)
