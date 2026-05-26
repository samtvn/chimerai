"""Orchestrator state definition"""

from typing import TypedDict, Optional, Any, Literal

from .models import OrchestratorSearchPlan, OrchestratorDecision
from apps.api.MarketAnalysisAgent.models import MarketAnalysisResult


class OrchestratorState(TypedDict, total=False):
    """State for the Orchestrator LangGraph workflow"""

    # Cellar analysis
    cellar_analysis: Optional[Any]


    # Structured search output
    search_plan: Optional[OrchestratorSearchPlan]

    # Market analysis output
    market_analysis_results: Optional[list[MarketAnalysisResult]]

    # Persisted recommendations
    recommendations_saved: int

    # Decision flags
    needs_market_analysis: bool
    missing_wine_categories: list[str]

    # Actions to trigger
    should_call_market_analysis: bool

    # Error tracking
    error: Optional[str]

    # Trigger event
    trigger_event: Optional[str]

    workflow_phase: Optional[str]

    orchestrator_decision: Optional[OrchestratorDecision]

    completed_steps: list[str]

    sales_analysis_results: Optional[dict]
