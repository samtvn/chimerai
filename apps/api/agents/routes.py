"""
Agent Routes
============
Manual trigger endpoint for the orchestrator.
The automatic trigger happens via the event_bus listener in runner.py.
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from apps.api.agents.runner import run_once

router = APIRouter(prefix="/api/agents", tags=["agents"])


class TriggerRequest(BaseModel):
    trigger: str = "Manually triggered: analyze the cellar and take appropriate action."


@router.post("/run")
async def run_agent(request: TriggerRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger the orchestrator.
    The agent runs in the background; events stream via SSE at /sse/stream.
    """
    background_tasks.add_task(run_once, request.trigger)
    return {"status": "started", "trigger": request.trigger}


@router.post("/run/sync")
async def run_agent_sync(request: TriggerRequest):
    """
    Trigger the orchestrator and wait for the final response.
    Useful for testing. For production use /run (background) + SSE stream.
    """
    result = await run_once(request.trigger)
    return {"status": "completed", "result": result}
