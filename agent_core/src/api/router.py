from .v1.router import router as v1_router
from .v1.router import lifespan as v1_lifespan
from fastapi import APIRouter


router = APIRouter()
router.include_router(v1_router, prefix="/v1")
