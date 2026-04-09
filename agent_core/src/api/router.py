from fastapi import APIRouter
from .v4.router import router as v4_router


router = APIRouter()
router.include_router(v4_router, prefix="/v4")
