"""
SSE Broadcaster
===============
Handles server-sent event streaming from the event bus to connected clients.
The FastAPI route in routes/sse.py delegates to these helpers.
"""

import asyncio

from fastapi import Request

from apps.api.events.bus import event_bus


async def event_generator(request: Request):
    """Yields SSE-formatted events from the event bus to a connected client."""
    queue = event_bus.subscribe()
    try:
        # Replay recent history so the client gets context on connect
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
