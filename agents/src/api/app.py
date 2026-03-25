# agent_policy_ollama/src/api/router.py
from fastapi import FastAPI
from .router import router, v2_lifespan

# -------------------------------------------------
# FastAPI Application
# -------------------------------------------------
app = FastAPI(title="Agent Policy Ollama API", version="0.2.0", lifespan=v2_lifespan)
app.include_router(router)
