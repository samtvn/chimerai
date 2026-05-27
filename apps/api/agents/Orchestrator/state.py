from typing import Any, Optional, TypedDict
from apps.api.agents.WineCellarAgent.models import Recommendation
from apps.api.events import Event


class OrchestratorState(TypedDict, total=False):
    """State for the Orchestrator LangGraph workflow"""

    trigger_event: Optional[Event]
    cellar_analysis: Optional[list[Recommendation]]
    sales_analysis: Optional[Any]
    market_analysis: Optional[Any]

    validated_analysis: Optional[Any]
    analysis_query: Optional[str]
    sales_query: Optional[str]
    market_analysis_query: Optional[str]
    next_node: Optional[str]
    workflow_phase: Optional[str]
    router_iterations: int
    market_analysis_started_at: Optional[str]
    recommendations_saved: Optional[int]
