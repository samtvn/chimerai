"""Service module for Orchestrator - provides high-level interface"""
from uuid import UUID
from api.Orchestrator.orchestrator import CellarOrchestrator
from database.repositories.cellar_repository import CellarRepository


class OrchestratorService:
    """High-level service for orchestrator workflows"""

    @staticmethod
    async def analyze_and_decide(
        cellar_repo: CellarRepository,
        user_id: UUID | None = None,
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
        return await orchestrator.run()
