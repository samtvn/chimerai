"""State definition for Sales Analysis Agent."""
from typing import Optional, TypedDict

from .models import SalesAnalysisFocus, SalesAnalysisResult, SalesRecommendationPlan


class SalesAnalysisAgentState(TypedDict, total=False):
    """State for the Sales Analysis LangGraph workflow."""

    focus_input: Optional[SalesAnalysisFocus | dict]
    focus: Optional[SalesAnalysisFocus]

    sales_data: Optional[dict]
    trend_analysis: Optional[str]
    recommendation_plan: Optional[SalesRecommendationPlan]

    analysis_result: Optional[SalesAnalysisResult]
    error: Optional[str]
