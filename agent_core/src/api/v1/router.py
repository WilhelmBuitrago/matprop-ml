from fastapi import APIRouter, FastAPI
from .scheme import Tools, CompletionRequest
from tools.config import AVAILABLES_TOOLS
from .service import CompletionService
from contextlib import asynccontextmanager
import requests

router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_service
    chat_service = CompletionService()
    yield


@router.get("/tools", response_model=Tools)
def get_tools():
    return {"tools": AVAILABLES_TOOLS}


@router.post("/completions")
def chat(request: CompletionRequest):
    response = chat_service.chat(request)
    return response


@router.get("/historial_summary")
def historial_summary_endpoint():
    response = requests.get("http://localhost:8001/v1/historial_summary")
    return response.json()


@router.get("/clear_history")
def clear_history_endpoint():
    response = requests.get("http://localhost:8001/v1/clear_history")
    return response.json()


@router.get("/conversation_history")
def conversation_history_endpoint():
    response = requests.get("http://localhost:8001/v1/conversation_history")
    return response.json()


@router.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    print(AVAILABLES_TOOLS)
