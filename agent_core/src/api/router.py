from fastapi import APIRouter
from .v3.router import router as v3_router


router = APIRouter()
router.include_router(v3_router, prefix="/v3")
