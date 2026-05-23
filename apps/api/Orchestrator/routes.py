"""FastAPI routes for the Orchestrator agent."""

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.Orchestrator.service import OrchestratorService
from apps.api.database.dependencies import get_read_db, get_demo_user_id
from apps.api.database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/run")
async def run_orchestrator(
    trigger_event: str | None = Query(default="wine_sold"),
    db=Depends(get_read_db),
):
    """Run the orchestrator workflow and return the analysis output."""
    try:
        user_id = await get_demo_user_id(db)
        cellar_repo = CellarRepository(db, read_only=True)
        return await OrchestratorService.analyze_and_decide(
            cellar_repo=cellar_repo,
            user_id=user_id,
            trigger_event=trigger_event,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestrator failed: {str(e)}")
