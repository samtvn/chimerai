"""State definition for Wine Cellar Analysis Agent"""
from typing import Any, Optional, TypedDict

from .models import RecommendationPlan, WineCellarAnalysis


class WineCellarAgentState(TypedDict, total=False):
    """State for the Wine Cellar Analysis LangGraph workflow"""

    # Input data
    wines_data: dict[str, Any]

    # Analysis steps
    diversity_analysis: Optional[str]
    strengths_analysis: Optional[str]
    weaknesses_analysis: Optional[str]
    recommendations_draft: Optional[str]
    recommendation_plan: Optional[RecommendationPlan]

    # Final output
    analysis_result: Optional[WineCellarAnalysis]

    # Error tracking
    error: Optional[str]
