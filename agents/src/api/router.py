# agent_policy_ollama/src/api/router.py
from .v2.router import router as v2_router
from .v2.router import lifespan as v2_lifespan
from fastapi import APIRouter


router = APIRouter()
router.include_router(v2_router, prefix="/v2")
