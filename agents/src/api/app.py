# agent_policy_ollama/src/api/router.py
from fastapi import FastAPI
from .router import v1_lifespan, router

# -------------------------------------------------
# FastAPI Application
# -------------------------------------------------
app = FastAPI(title="Agent Policy Ollama API", version="0.1.0", lifespan=v1_lifespan)
app.include_router(router)
