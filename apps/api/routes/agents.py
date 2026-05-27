"""
Agent Routes
============
Manual trigger endpoint for the orchestrator.
The automatic trigger happens via the event_bus listener in events/handlers/orchestrator_trigger.py.
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from apps.api.events.bus import AgentEvent
from apps.api.events.handlers.orchestrator_trigger import run_once

router = APIRouter(prefix="/api/agents", tags=["agents"])


class TriggerRequest(BaseModel):
    trigger: str = "Manually triggered: analyze the cellar and take appropriate action."


@router.post("/run")
async def run_agent(request: TriggerRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger the orchestrator.
    The agent runs in the background; events stream via SSE at /sse/stream.
    """
    background_tasks.add_task(
        run_once, AgentEvent(source="api", type="analysis_run", message=request.trigger)
    )
    return {"status": "started", "trigger": request.trigger}


@router.post("/run/sync")
async def run_agent_sync(request: TriggerRequest):
    """
    Trigger the orchestrator and wait for the final response.
    Useful for testing. For production use /run (background) + SSE stream.
    """
    result = await run_once(AgentEvent(source="api", type="analysis_run", message=request.trigger))
    return {"status": "completed", "result": result}


@router.post("/analyse")
async def run_analysis(background_tasks: BackgroundTasks):
    """
    Alias for /run with a default trigger message.
    """
    background_tasks.add_task(
        run_once, AgentEvent(source="api", type="analysis_run", message="Full analysis")
    )
    return {"status": "started"}
