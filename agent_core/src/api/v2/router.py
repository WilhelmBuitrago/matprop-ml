from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from .scheme import CompletionRequestV2
from .service import CompletionServiceV2

router = APIRouter()
service_v2 = CompletionServiceV2()


@router.post("/completions")
def chat_v2(request: CompletionRequestV2, http_request: Request):
    accept_header = http_request.headers.get("accept", "").lower()
    wants_stream = request.stream or "text/event-stream" in accept_header

    if wants_stream:
        return StreamingResponse(
            service_v2.stream_chat_events(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return service_v2.chat(request)
