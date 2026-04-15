from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
import logging
import os
import time
import uuid

from infrastructure.logging import configure_logging, reset_request_id, set_request_id

from .router import router


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


ALLOWED_ORIGINS = _parse_cors_origins()
ALLOW_CREDENTIALS = "*" not in ALLOWED_ORIGINS
configure_logging()
logger = logging.getLogger(__name__)


async def _lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Agent Core API", version="4.0.0", lifespan=_lifespan)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = set_request_id(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed method=%s path=%s",
            request.method,
            request.url.path,
        )
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "http_request method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        reset_request_id(token)

    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
