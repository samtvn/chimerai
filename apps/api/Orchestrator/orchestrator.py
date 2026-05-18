"""Orchestrator Agent for wine cellar management"""
import asyncio
from langgraph.graph import StateGraph, END
from .state import OrchestratorState
from api.WineCellarAgent.service import WineCellarAnalysisService
from .event_manager import event_manager, Event
from .events import AnalysisRunEvent, WineSoldEvent
import uuid
from sqlalchemy.ext.asyncio import AsyncSession


class CellarOrchestrator:
    """Orchestrator for wine cellar analysis and market research workflows"""

    def __init__(self, db: AsyncSession):
        """Initialize the orchestrator"""
        if db is None:
            raise ValueError("db session is required")
        self.db = db
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(OrchestratorState)

        workflow.add_node("decide_entry", self._decide_entry_point)
        workflow.add_node("analyze_cellar", self._analyze_cellar)
        workflow.add_node("evaluate_gaps", self._evaluate_gaps)
        workflow.add_node("decide_market_analysis", self._decide_market_analysis)

        workflow.set_entry_point("decide_entry")

        workflow.add_conditional_edges(
            "decide_entry",
            self._should_analyze_cellar,
            {
                "analyze": "analyze_cellar",
                "end": END,
            },
        )
        workflow.add_edge("analyze_cellar", "evaluate_gaps")
        workflow.add_edge("evaluate_gaps", "decide_market_analysis")
        workflow.add_edge("decide_market_analysis", END)

        return workflow.compile()

    async def _decide_entry_point(self, state: OrchestratorState):
        """
        Checks for a trigger event and decides whether to start the analysis.
        """
        print("[Orchestrator] Checking for trigger event...")
        last_event = event_manager.get_last_event()
        if last_event and isinstance(last_event, WineSoldEvent):
            print(f"[Orchestrator] Detected '{last_event.event_type}' event. Triggering analysis.")
            state["trigger_event"] = last_event.event_type
        else:
            print("[Orchestrator] No trigger event detected.")
            state["trigger_event"] = None
        return state

    def _should_analyze_cellar(self, state: OrchestratorState) -> str:
        """
        Determines if the cellar analysis should run based on the trigger event.
        """
        if state.get("trigger_event") == "wine_sold":
            return "analyze"
        return "end"

    async def _analyze_cellar(self, state: OrchestratorState) -> OrchestratorState:
        """Run the wine cellar analysis"""
        print("[Orchestrator] Running cellar analysis...")
        service = WineCellarAnalysisService()
        analysis = await service.analyze_cellar(self.db)
        state["cellar_analysis"] = analysis

        # Add analysis event
        analysis_id = str(uuid.uuid4())
        event = AnalysisRunEvent(agent_name="WineCellarAnalysisAgent", analysis_id=analysis_id)
        event_manager.add_event(event)
        state["analysis_id"] = analysis_id

        print(f"[Orchestrator] Cellar analysis complete. Analysis ID: {analysis_id}")

        return state

    async def _evaluate_gaps(self, state: OrchestratorState) -> OrchestratorState:
        """Evaluate gaps in the cellar based on weaknesses"""
        try:
            analysis = state.get("cellar_analysis")
            if not analysis:
                state["error"] = "No analysis available to evaluate"
                return state

            print("\n[Orchestrator] Evaluating cellar gaps...")

            # Extract missing categories from weaknesses and recommendations
            missing_categories = []

            # Check weaknesses for patterns
            for weakness in analysis.weaknesses:
                weakness_lower = weakness.lower()
                if "new world" in weakness_lower or "geographic" in weakness_lower:
                    missing_categories.append("New World wines")
                if "light" in weakness_lower or "fresh" in weakness_lower:
                    missing_categories.append("Light/fresh reds")
                if "fortified" in weakness_lower or "sherry" in weakness_lower:
                    missing_categories.append("Fortified wines")
                if "varietal" in weakness_lower or "monoculture" in weakness_lower:
                    missing_categories.append("Diverse varietals")

            # Check recommendations for action items
            for rec in analysis.recommendations:
                if rec.criticality.value in ["high", "critical"]:
                    missing_categories.append(rec.title)
                elif rec.criticality.value == "medium":
                    missing_categories.append(rec.title)

            # Deduplicate
            missing_categories = list(dict.fromkeys(missing_categories))

            state["missing_wine_categories"] = missing_categories

            # If there are gaps, we need market analysis
            if missing_categories:
                state["needs_market_analysis"] = True
                print(f"\n[Orchestrator] Found {len(missing_categories)} wine categories to address:")
                for cat in missing_categories:
                    print(f"  - {cat}")
            else:
                print("\n[Orchestrator] Cellar is well-balanced, no gaps detected")
                state["needs_market_analysis"] = False

            return state

        except Exception as e:
            state["error"] = f"Gap evaluation failed: {str(e)}"
            return state

    async def _decide_market_analysis(self, state: OrchestratorState) -> OrchestratorState:
        """Decide whether to trigger market analysis"""
        try:
            if state.get("needs_market_analysis"):
                state["should_call_market_analysis"] = True
                print("\n>>> Call the wine market analysis")
            else:
                print("\n[Orchestrator] No significant gaps detected. Market analysis not required.")
        except Exception as e:
            state["error"] = f"Decision making failed: {str(e)}"
        return state

    async def run(self) -> OrchestratorState:
        """Execute the orchestrator workflow"""
        try:
            initial_state: OrchestratorState = {
                "needs_market_analysis": False,
                "missing_wine_categories": [],
                "should_call_market_analysis": False,
            }
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            print(f"[Orchestrator] Workflow failed: {str(e)}")
            raise
