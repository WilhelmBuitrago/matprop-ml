# backend_llm/src/app.py
import logging
from fastapi import FastAPI, HTTPException
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


app = FastAPI(title="MatProp LLM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent: Optional[ChatAgent] = None

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


# ------------------------------
# Endpoints
# -----------------------------
@app.post("/v1/configure")
def configure_endpoint(cfg: ConfigureRequest):
    global agent

    config = ChatConfig(
        model_endpoint=cfg.model_endpoint,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        max_context_tokens=cfg.max_context_tokens,
        cache_dir=cfg.cache_dir,
        system_prompt=cfg.system_prompt,
    )

    agent = ChatAgent(config)

    return {"status": "configured", "config": config.__dict__}


@app.post("/v1/chat")
def chat_endpoint(req: ChatRequest):

    global agent
    # logger.info(f"Received chat message: {req.message}")
    if agent is None:
        # logger.info("Agent not initialized. Initializing default agent.")
        agent = init_default_agent()

    # logger.info("agent: {}".format(agent))
    try:
        response = agent.chat(req.messages)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model backend error: {str(e)}")
    """
    global agent
    response = "Todo funcionando correctamente!"
    return {"response": response}
    """


@app.get("/v1/historial_summary")
def historial_summary_endpoint():
    global agent

    if agent is None:
        return {"summary": ""}

    return {"summary": agent.get_conversation_summary()}


@app.get("/v1/clear_history")
def clear_history_endpoint():
    global agent

    if agent is None:
        return {"status": "already empty"}

    agent.clear_history()
    return {"status": "history cleared"}


@app.get("/v1/conversation_history")
def conversation_history_endpoint():
    global agent

    if agent is None:
        return {"history": []}

    return {"history": agent.conversation_history}


# -------------------------------------------------
# Health check endpoint
# -------------------------------------------------
@app.get("/v1/health")
def health():
    return {"status": "ok"}
