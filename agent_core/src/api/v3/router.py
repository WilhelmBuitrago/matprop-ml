from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .scheme import CompletionRequestV3
from .service import CompletionServiceV3


router = APIRouter()
service_v3 = CompletionServiceV3()


@router.post("/completions")
def chat_v3(request: CompletionRequestV3, http_request: Request):
    """V3 endpoint with optional SSE streaming."""
    accept_header = http_request.headers.get("accept", "").lower()
    wants_stream = request.stream or "text/event-stream" in accept_header

    if wants_stream:
        return StreamingResponse(
            service_v3.stream_chat_events(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return service_v3.chat(request)
