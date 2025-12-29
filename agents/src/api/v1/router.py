from fastapi import APIRouter, FastAPI
from .scheme import IntentionRequest, CompletionRequest
from .service import (
    PlanningService,
    ChatService,
    InfoService,
    LoadModelsService,
)
from contextlib import asynccontextmanager
from fastapi.concurrency import run_in_threadpool

# -------------------------------------------------
# Initialization
# -------------------------------------------------
info_service: InfoService | None = None
planning_service: PlanningService | None = None
chat_service: ChatService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global planning_service, info_service, chat_service
    load_models_service = LoadModelsService()
    load_models_service.download_models()
    planning_service = PlanningService()
    info_service = InfoService()
    chat_service = ChatService()
    yield


router = APIRouter()


@router.post("/intention")
def get_intentions(request: IntentionRequest):
    response = planning_service.plan(request)
    return response


@router.post("/completions")
def get_completions(request: CompletionRequest):
    response = chat_service.chat(request)
    return response


@router.get("/info")
def get_info():
    return info_service.get_info()


@router.get("/health")
def health_check():
    return {"status": "ok"}
