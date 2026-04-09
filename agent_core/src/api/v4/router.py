from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .scheme import CompletionRequestV4
from .service import PlannedRuntimeV4Service


router = APIRouter()
service = PlannedRuntimeV4Service()


@router.post("/completions")
def chat_v4(request: CompletionRequestV4):
    """V4 endpoint with optional SSE streaming."""
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
