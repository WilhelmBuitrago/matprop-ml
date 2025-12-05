# llamat2-chat/src/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from model import generate_response
from preload_model import (
    CACHE_DIR,
    load_model_from_files,
    detect_gpu,
    select_load_kwargs,
    detect_ram,
    serialize_kwargs,
)
import hashlib


class CompletionRequest(BaseModel):
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 200
    stop: Optional[List[str]] = None


class ChatRequest(BaseModel):
    message: str


model = None
tokenizer = None


# -------------------------------------------------
# Inicializar modelo una sola vez
# -------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    model, tokenizer = load_model_from_files()
    # agent = ChatAgent(model, tokenizer, ChatConfig())
    yield
    # Aquí puedes liberar recursos si quieres (opcional)
    # model.free() / del agent / etc.


app = FastAPI(lifespan=lifespan)


# -------------------------------------------------
# Endpoint
# -------------------------------------------------
@app.post("/v1/generate_response")
def generate_response_endpoint(req: ChatRequest):
    response = generate_response(model, tokenizer, req.message, max_tokens=200)
    return {"response": response}


@app.post("/v1/completions")
def completions_endpoint(payload: CompletionRequest):
    """Compatibility endpoint that accepts completion-style payloads
    and returns a response with `choices[0].text` like OpenAI-style APIs.
    """
    prompt = payload.prompt
    text = generate_response(
        model,
        tokenizer,
        prompt,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
        stop=payload.stop,
    )

    resp = {
        "id": hashlib.md5(text.encode()).hexdigest(),
        "object": "text_completion",
        "choices": [{"text": text}],
        "usage": {
            "prompt_tokens": len(prompt) // 4,
            "completion_tokens": len(text) // 4,
            "total_tokens": (len(prompt) + len(text)) // 4,
        },
    }
    return resp


@app.get("/v1/detect_gpu")
def detect_gpu_endpoint():
    gpu_info = detect_gpu()
    return gpu_info


@app.get("/v1/detect_ram")
def detect_ram_endpoint():
    ram_info = detect_ram()
    return {"ram_gb": ram_info}


@app.get("/v1/load_kwargs")
def load_kwargs_endpoint():
    kwargs = select_load_kwargs(has_gpu=detect_gpu()[0], vram_gb=detect_gpu()[1])
    return serialize_kwargs(kwargs)


# -------------------------------------------------
# Health check endpoint
# -------------------------------------------------
@app.get("/v1/health")
def health():
    return {"status": "ok"}
