from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from .router import router
from .router import v1_lifespan
import os


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


ALLOWED_ORIGINS = _parse_cors_origins()
ALLOW_CREDENTIALS = "*" not in ALLOWED_ORIGINS

app = FastAPI(title="Agent Core API", version="0.1.0", lifespan=v1_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
