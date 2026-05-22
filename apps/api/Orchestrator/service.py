"""Service module for Orchestrator - provides high-level interface"""
from uuid import UUID
import asyncio
from .orchestrator import CellarOrchestrator
from database.repositories.cellar_repository import CellarRepository
from agents.event_bus import event_bus, AgentEvent
from database.database import AsyncReadSessionLocal
from database.dependencies import get_demo_user_id


class OrchestratorService:
    """High-level service for orchestrator workflows"""

    @staticmethod
    async def analyze_and_decide(
        cellar_repo: CellarRepository,
        user_id: UUID | None = None,
        trigger_event: str | None = None,
    ):
        """
        Run the complete orchestrator workflow:
        1. Analyze wine cellar
        2. Identify missing wine categories
        3. Decide if market analysis is needed

        Returns:
            dict: Orchestrator result with analysis and decisions
        """
        orchestrator = CellarOrchestrator(cellar_repo, user_id=user_id)
        return await orchestrator.run(trigger_event=trigger_event)

    @staticmethod
    async def run_event_listener():
        queue = event_bus.subscribe()
        try:
            while True:
                event: AgentEvent = await queue.get()
                if event.type != "wine_sold":
                    continue
                async with AsyncReadSessionLocal() as session:
                    user_id = await get_demo_user_id(session)
                    cellar_repo = CellarRepository(session, read_only=True)
                    orchestrator = CellarOrchestrator(cellar_repo, user_id=user_id)
                    await orchestrator.run(trigger_event="wine_sold")
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(queue)
