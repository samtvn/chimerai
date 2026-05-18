"""State definition for Wine Cellar Analysis Agent"""
from typing import TypedDict, Optional, Any, List
from .models import WineCellarAnalysis


class WineCellarAgentState(TypedDict, total=False):
    """State for the Wine Cellar Analysis LangGraph workflow"""
    
    # Input data
    wines_data: dict[str, Any]
    
    # Analysis steps
    diversity_analysis: Optional[str]
    strengths_analysis: Optional[str]
    weaknesses_analysis: Optional[str]
    recommendations_draft: Optional[str]
    
    # Final output
    analysis_result: Optional[WineCellarAnalysis]
    
    # Error tracking
    error: Optional[str]
