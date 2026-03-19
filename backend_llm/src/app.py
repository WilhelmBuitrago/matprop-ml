# backend_llm/src/app.py
import logging
import os
import threading
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from chat_agent import ChatAgent, ChatConfig

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class ConfigureRequest(BaseModel):
    model_endpoint: str = "http://llamat2-chat:8002/v1/completions"
    temperature: float = 0.7
    max_tokens: int = 256
    max_context_tokens: int = 512
    cache_dir: Optional[str] = None
    system_prompt: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="MatProp LLM Backend")

ALLOWED_ORIGINS = _parse_cors_origins()
ALLOW_CREDENTIALS = "*" not in ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_COOKIE_NAME = "matprop_session_id"
SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7

_agents_by_session: Dict[str, ChatAgent] = {}
_config_by_session: Dict[str, ChatConfig] = {}
_sessions_lock = threading.RLock()

# ------------------------------
# Helpers
# ------------------------------


def init_default_agent():
    return ChatAgent(
        ChatConfig(
            model_endpoint="http://agents:8003/v1/completions",
            temperature=0.7,
            max_tokens=256,
            max_context_tokens=2096,
            cache_dir="/data/cache",
        )
    )


def _get_or_create_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        return session_id

    session_id = str(uuid4())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
    )
    return session_id


def _get_or_create_agent(session_id: str) -> ChatAgent:
    with _sessions_lock:
        existing = _agents_by_session.get(session_id)
        if existing is not None:
            return existing

        cfg = _config_by_session.get(session_id)
        created = ChatAgent(cfg) if cfg else init_default_agent()
        _agents_by_session[session_id] = created
        return created


# ------------------------------
# Endpoints
# -----------------------------
@app.post("/v1/configure")
def configure_endpoint(cfg: ConfigureRequest, request: Request, response: Response):
    session_id = _get_or_create_session_id(request, response)

    config = ChatConfig(
        model_endpoint=cfg.model_endpoint,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        max_context_tokens=cfg.max_context_tokens,
        cache_dir=cfg.cache_dir,
        system_prompt=cfg.system_prompt,
    )

    with _sessions_lock:
        _config_by_session[session_id] = config
        _agents_by_session[session_id] = ChatAgent(config)

    return {
        "status": "configured",
        "session_id": session_id,
        "config": config.__dict__,
    }


@app.post("/v1/chat")
def chat_endpoint(req: ChatRequest, request: Request, response: Response):
    session_id = _get_or_create_session_id(request, response)
    agent = _get_or_create_agent(session_id)

    try:
        model_response = agent.chat(req.messages)
        return {"session_id": session_id, "response": model_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model backend error: {str(e)}")
    """
    global agent
    response = "Todo funcionando correctamente!"
    return {"response": response}
    """


@app.get("/v1/historial_summary")
def historial_summary_endpoint(request: Request, response: Response):
    session_id = _get_or_create_session_id(request, response)
    agent = _agents_by_session.get(session_id)

    if agent is None:
        return {"summary": ""}

    return {"session_id": session_id, "summary": agent.get_conversation_summary()}


@app.post("/v1/clear_history")
def clear_history_endpoint(request: Request, response: Response):
    session_id = _get_or_create_session_id(request, response)
    agent = _agents_by_session.get(session_id)

    if agent is None:
        return {"session_id": session_id, "status": "already empty"}

    agent.clear_history()
    return {"session_id": session_id, "status": "history cleared"}


@app.get("/v1/clear_history")
def clear_history_endpoint_deprecated(request: Request, response: Response):
    logger.warning("GET /v1/clear_history is deprecated. Use POST /v1/clear_history")
    return clear_history_endpoint(request, response)


@app.get("/v1/conversation_history")
def conversation_history_endpoint(request: Request, response: Response):
    session_id = _get_or_create_session_id(request, response)
    agent = _agents_by_session.get(session_id)

    if agent is None:
        return {"session_id": session_id, "history": []}

    return {"session_id": session_id, "history": agent.conversation_history}


# -------------------------------------------------
# Health check endpoint
# -------------------------------------------------
@app.get("/v1/health")
def health():
    return {"status": "ok"}
