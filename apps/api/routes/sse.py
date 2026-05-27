from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from apps.api.events.bus import event_bus
from apps.api.events.handlers.sse_broadcaster import event_generator

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/stream")
async def agent_stream(request: Request):
    return EventSourceResponse(event_generator(request))


@router.get("/status")
async def agent_status():
    return {
        "status": "idle",
        "subscriber_count": event_bus.subscriber_count,
        "recent_events": len(event_bus.get_history()),
    }
