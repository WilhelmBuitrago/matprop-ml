from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import logging

from api.security import enforce_request_security
from .scheme import CompletionRequestV4
from .service import PlannedRuntimeV4Service


router = APIRouter()
service = PlannedRuntimeV4Service()
logger = logging.getLogger(__name__)


@router.post("/completions", dependencies=[Depends(enforce_request_security)])
def chat_v4(http_request: Request, request: CompletionRequestV4):
    """V4 endpoint with optional SSE streaming."""
    logger.info(
        "chat_v4_request_received method=%s path=%s stream=%s",
        http_request.method,
        http_request.url.path,
        request.stream,
    )
    if request.stream:
        return StreamingResponse(
            service.stream_chat_events(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return service.chat(request)
