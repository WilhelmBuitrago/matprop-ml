# agent_policy_ollama/src/api/router.py
from .v1.router import router as v1_router
from .v1.router import lifespan as v1_lifespan
from .v2.router import router as v2_router
from fastapi import APIRouter


router = APIRouter()
router.include_router(v1_router, prefix="/v1")
router.include_router(v2_router, prefix="/v2")
