"""Orchestrator state definition"""
from typing import TypedDict, Optional, Any

from .models import OrchestratorSearchPlan
from api.MarketAnalysisAgent.models import MarketAnalysisResult


class OrchestratorState(TypedDict, total=False):
    """State for the Orchestrator LangGraph workflow"""

    # Cellar analysis
    cellar_analysis: Optional[Any]

    # Structured search output
    search_plan: Optional[OrchestratorSearchPlan]

    # Market analysis output
    market_analysis_results: Optional[list[MarketAnalysisResult]]

    # Decision flags
    needs_market_analysis: bool
    missing_wine_categories: list[str]

    # Actions to trigger
    should_call_market_analysis: bool

    # Error tracking
    error: Optional[str]

    # Trigger event
    trigger_event: Optional[str]
