"""Orchestrator state definition"""
from typing import TypedDict, Optional, Any


class OrchestratorState(TypedDict, total=False):
    """State for the Orchestrator LangGraph workflow"""
    
    # Cellar analysis
    cellar_analysis: Optional[Any]
    
    # Decision flags
    needs_market_analysis: bool
    missing_wine_categories: list[str]
    
    # Actions to trigger
    should_call_market_analysis: bool
    
    # Error tracking
    error: Optional[str]
    
    # Trigger event
    trigger_event: Optional[str]
