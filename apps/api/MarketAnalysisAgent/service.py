"""Service layer for Market Analysis Agent"""
from typing import Any, Mapping

from api.MarketAnalysisAgent.agent import MarketAnalysisAgent
from api.MarketAnalysisAgent.models import MarketAnalysisCriteria, MarketAnalysisResult


class MarketAnalysisService:
    """High-level service for market analysis"""

    @staticmethod
    async def analyze_recommendation(
        criteria: MarketAnalysisCriteria | Mapping[str, Any],
        quantity: int,
        recommendation_title: str,
    ) -> MarketAnalysisResult:
        """Analyze a single recommendation against market inventory."""
        if isinstance(criteria, MarketAnalysisCriteria):
            criteria_model = criteria
        else:
            criteria_model = MarketAnalysisCriteria(**criteria)

        agent = MarketAnalysisAgent()
        return await agent.analyze_recommendation(
            criteria=criteria_model,
            quantity=quantity,
            recommendation_title=recommendation_title,
        )
