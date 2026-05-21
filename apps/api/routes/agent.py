from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api/agent", tags=["agent"])


class TriggerRequest(BaseModel):
    trigger: str = "manual"
    data: dict | None = None


@router.post("/trigger")
async def trigger_agent(body: TriggerRequest = None):
    if body is None:
        body = TriggerRequest()

    asyncio.create_task(run_orchestrator(trigger=body.trigger, data=body.data))
    return {"status": "started", "trigger": body.trigger}
