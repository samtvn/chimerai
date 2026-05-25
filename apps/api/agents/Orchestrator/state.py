from typing import TypedDict, Optional, Any, Literal

class OrchestratorState(TypedDict, total=False):
    """State for the Orchestrator LangGraph workflow"""

    cellar_analysis: Optional[Any]
