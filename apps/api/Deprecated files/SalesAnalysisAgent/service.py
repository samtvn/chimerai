"""Service module for Sales Analysis Agent."""

from uuid import UUID

from .agent import SalesAnalysisAgent
from .models import SalesAnalysisFocus, SalesAnalysisResult
from apps.api.database.repositories.cellar_repository import CellarRepository


class SalesAnalysisService:
    """High-level service for sales analysis."""

    @staticmethod
    async def analyze_sales(
        cellar_repo: CellarRepository,
        user_id: UUID | None = None,
        lookback_days: int = 30,
        focus: SalesAnalysisFocus | dict | None = None,
    ) -> SalesAnalysisResult:
        """Analyze sales trends versus stock and return structured recommendations."""
        agent = SalesAnalysisAgent(
            cellar_repo=cellar_repo,
            user_id=user_id,
            lookback_days=lookback_days,
        )
        return await agent.analyze(focus=focus)
