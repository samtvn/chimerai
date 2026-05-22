"""Standalone event listener test script (no pytest)."""

import asyncio
import json
import sys
from contextlib import suppress
from pathlib import Path

API_PACKAGE_DIR = Path(__file__).resolve().parents[1]
if str(API_PACKAGE_DIR) not in sys.path:
    # Allow running directly without PYTHONPATH
    sys.path.insert(0, str(API_PACKAGE_DIR))

from agents.event_bus import event_bus, AgentEvent
from Orchestrator.service import OrchestratorService


async def _print_bus_events(duration_seconds: int = 10) -> None:
    queue = event_bus.subscribe()
    try:
        print(f"[test] Listening for bus events ({duration_seconds}s)...")
        end_time = asyncio.get_event_loop().time() + duration_seconds
        while asyncio.get_event_loop().time() < end_time:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            print(f"[bus] {event.type} from {event.source}: {event.message}")
    finally:
        event_bus.unsubscribe(queue)


async def main() -> None:
    print("[test] Starting orchestrator event listener...")
    listener_task = asyncio.create_task(OrchestratorService.run_event_listener())

    for _ in range(50):
        if event_bus.subscriber_count:
            break
        await asyncio.sleep(0)

    print("[test] Publishing wine_sold event...")
    await event_bus.publish(
        AgentEvent(
            source="test",
            type="wine_sold",
            message=json.dumps({"wine_id": 1, "quantity": 1, "type": "sale"}),
        )
    )

    await _print_bus_events(duration_seconds=10)

    print("[test] Stopping listener...")
    listener_task.cancel()
    with suppress(asyncio.CancelledError):
        await listener_task


if __name__ == "__main__":
    asyncio.run(main())
