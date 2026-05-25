from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from .state import OrchestratorState
import uuid
from uuid import UUID
from apps.api.database.repositories.cellar_repository import CellarRepository
from apps.api.agents.Orchestrator.checkpointer import get_checkpointer



class Orchestrator:
    """Orchestrator for wine cellar analysis and market research workflows"""

    def __init__(self, cellar_repo: CellarRepository, user_id: UUID | None = None):
        """Initialize the orchestrator"""
        if cellar_repo is None:
            raise ValueError("cellar_repo is required")
        self.cellar_repo = cellar_repo
        self.user_id = user_id
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(OrchestratorState)

        workflow.add_node("event_listener", self._event_listener)
        workflow.add_node("orchestrator_router", self._general_analysis_agent)
        workflow.add_node("analyze_cellar", self._analyze_cellar)
        workflow.add_node("run_market_analysis", self._run_market_analysis)
        workflow.add_node("persist_recommendations", self._persist_recommendations)
        workflow.add_node("sales_analysis", self._run_sales_analysis)
        workflow.add_node("update_menu", self._update_menu)

        workflow.set_entry_point("event_listener")
        workflow.add_edge("analyze_cellar", "run_market_analysis")
        workflow.add_edge("run_market_analysis", "orchestrator_router")
        workflow.add_edge("sales_analysis", "orchestrator_router")
        workflow.add_conditional_edges("orchestrator_router", self.route, {"sales_analysis": "sales_analysis",
                                                                      "run_market_analysis": "run_market_analysis",
                                                                      "analyze_cellar": "analyze_cellar"})
        workflow.add_conditional_edges("event_listener", self.event_analysis, {"orchestrator_router": "orchestrator_router",
                                                                               "update_menu": "update_menu"})
        workflow.add_edge("orchestrator_router", "persist_recommendations")
        workflow.add_edge("persist_recommendations", END)

        return workflow.compile(checkpointer=get_checkpointer())


    def _event_listener(self, state: OrchestratorState) -> OrchestratorState:
        ...


    def _orchestrator_router(self, state: OrchestratorState) -> str:
        """Determine the next step based on the current state"""
        if state.get("error"):
            return "general_analysis_agent"
        if state.get("should_call_market_analysis"):
            return "run_market_analysis"
        if state.get("needs_market_analysis"):
            return "run_market_analysis"
        if state.get("cellar_analysis") is None:
            return "analyze_cellar"
        return "general_analysis_agent"

    def _analyze_cellar(self, state: OrchestratorState) -> CompiledStateGraph:
        ...

    def _run_market_analysis(self, state: OrchestratorState) -> OrchestratorState:
        ...
    def _persist_recommendations(self, state: OrchestratorState) -> OrchestratorState:
        ...
    def _run_sales_analysis(self, state: OrchestratorState) -> OrchestratorState:
        ...
    def _update_menu(self, state: OrchestratorState) -> OrchestratorState:
        ...
    def _general_analysis_agent(self, state: OrchestratorState) -> OrchestratorState:
        ...

    @staticmethod
    def _print_graph(workflow: CompiledStateGraph):

        print(workflow.get_graph().print_ascii())


    def route(self, initial_state: OrchestratorState):
        ...

    def event_analysis(self, initial_state: OrchestratorState):
        ...
