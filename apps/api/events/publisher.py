"""
Publisher
=========
Convenience helpers for publishing standard domain events to the event bus.
Use these instead of constructing AgentEvent inline throughout the codebase.
"""

import json
from datetime import datetime, timezone

from apps.api.events.bus import AgentEvent, event_bus


async def publish_wine_sold(wine_id: str | int, quantity: int, source: str = "api") -> None:
    await event_bus.publish(
        AgentEvent(
            source=source,
            type="wine_sold",
            message=json.dumps({"wine_id": str(wine_id), "quantity": quantity}),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )


async def publish_wine_added(wine_id: str | int, quantity: int, source: str = "api") -> None:
    await event_bus.publish(
        AgentEvent(
            source=source,
            type="wine_added",
            message=json.dumps({"wine_id": str(wine_id), "quantity": quantity}),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )


async def publish_analysis_run(source: str = "api") -> None:
    await event_bus.publish(
        AgentEvent(
            source=source,
            type="analysis_run",
            message="Manual analysis run requested",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )


async def publish_agent_event(
    type: str, message: str, source: str = "orchestrator"
) -> None:
    """Generic helper for action/thought/observation/final/alert events."""
    await event_bus.publish(
        AgentEvent(
            source=source,
            type=type,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
