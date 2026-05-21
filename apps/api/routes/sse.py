from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import asyncio

from agents.event_bus import event_bus

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def event_generator(request: Request):
    queue = event_bus.subscribe()
    try:
        for event in event_bus.get_history(limit=20):
            if await request.is_disconnected():
                return
            yield {"event": "agent", "data": event.to_sse()}
            await asyncio.sleep(0.01)

        while True:
            if await request.is_disconnected():
                return
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield {"event": "agent", "data": event.to_sse()}
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}
    finally:
        event_bus.unsubscribe(queue)


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
