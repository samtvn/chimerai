"""Orchestrator Agent for wine cellar management"""
from langgraph.graph import StateGraph, END
from .state import OrchestratorState
from .event_manager import event_manager, Event
from .events import AnalysisRunEvent, WineSoldEvent
import uuid
from uuid import UUID
from ..database.repositories.cellar_repository import CellarRepository
from .models import MarketSearchCriteria, RecommendationSearchPlan, OrchestratorSearchPlan
from api.WineCellarAgent.models import CriticalityLevel, WineBuyingAspect, Recommendation


class CellarOrchestrator:
    """Orchestrator for wine cellar analysis and market research workflows"""

    def __init__(self, cellar_repo: CellarRepository, user_id: UUID | None = None):
        """Initialize the orchestrator"""
        if cellar_repo is None:
            raise ValueError("cellar_repo is required")
        self.cellar_repo = cellar_repo
        self.user_id = user_id
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(OrchestratorState)

        workflow.add_node("decide_entry", self._decide_entry_point)
        workflow.add_node("analyze_cellar", self._analyze_cellar)
        workflow.add_node("build_search_plan", self._build_search_plan)
        workflow.add_node("run_market_analysis", self._run_market_analysis)

        workflow.set_entry_point("decide_entry")

        workflow.add_conditional_edges(
            "decide_entry",
            self._should_analyze_cellar,
            {
                "analyze": "analyze_cellar",
                "end": END,
            },
        )
        workflow.add_edge("analyze_cellar", "build_search_plan")
        workflow.add_conditional_edges(
            "build_search_plan",
            self._should_run_market_analysis,
            {
                "market_analysis": "run_market_analysis",
                "end": END,
            },
        )
        workflow.add_edge("run_market_analysis", END)

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
        from api.WineCellarAgent.service import WineCellarAnalysisService

        service = WineCellarAnalysisService()
        analysis = await service.analyze_cellar(self.cellar_repo, user_id=self.user_id)
        state["cellar_analysis"] = analysis

        # Add analysis event
        analysis_id = str(uuid.uuid4())
        event = AnalysisRunEvent(agent_name="WineCellarAnalysisAgent", analysis_id=analysis_id)
        event_manager.add_event(event)
        state["analysis_id"] = analysis_id

        print(f"[Orchestrator] Cellar analysis complete. Analysis ID: {analysis_id}")

        return state

    def _criticality_rank(self, criticality: CriticalityLevel) -> int:
        """Return the execution order for a recommendation criticality."""
        return {
            CriticalityLevel.CRITICAL: 1,
            CriticalityLevel.HIGH: 2,
            CriticalityLevel.MEDIUM: 3,
            CriticalityLevel.LOW: 4,
        }.get(criticality, 4)

    def _should_call_market_analysis(self, recommendation: Recommendation, priority_rank: int) -> bool:
        """Decide whether a recommendation should trigger market analysis."""
        if priority_rank == 1:
            return True
        return recommendation.criticality in {CriticalityLevel.CRITICAL, CriticalityLevel.HIGH}

    def _build_criteria(self, recommendation: Recommendation) -> MarketSearchCriteria:
        """Convert a structured recommendation into search-only criteria."""
        criteria_values: dict[str, str] = {"price_range": recommendation.price_range}

        for parameter in recommendation.parameters:
            if parameter.aspect == WineBuyingAspect.COLOUR and "colour" not in criteria_values:
                criteria_values["colour"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.COUNTRY and "country" not in criteria_values:
                criteria_values["country"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.REGION and "region" not in criteria_values:
                criteria_values["region"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.SUB_REGION and "sub_region" not in criteria_values:
                criteria_values["sub_region"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.GRAPE_VARIETY and "grape_variety" not in criteria_values:
                criteria_values["grape_variety"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.STYLE and "style" not in criteria_values:
                criteria_values["style"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.VINTAGE and "vintage" not in criteria_values:
                criteria_values["vintage"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.ALCOHOL_LEVEL and "alcohol_level" not in criteria_values:
                criteria_values["alcohol_level"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.TANNIN and "tannin" not in criteria_values:
                criteria_values["tannin"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.ACIDITY and "acidity" not in criteria_values:
                criteria_values["acidity"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.SWEETNESS and "sweetness" not in criteria_values:
                criteria_values["sweetness"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.BODY and "body" not in criteria_values:
                criteria_values["body"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.AGEING_POTENTIAL and "ageing_potential" not in criteria_values:
                criteria_values["ageing_potential"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.FOOD_PAIRING and "food_pairing" not in criteria_values:
                criteria_values["food_pairing"] = parameter.target

        return MarketSearchCriteria(**criteria_values)

    def _should_run_market_analysis(self, state: OrchestratorState) -> str:
        """Route to market analysis if any recommendation requires it."""
        if state.get("needs_market_analysis"):
            return "market_analysis"
        return "end"

    async def _build_search_plan(self, state: OrchestratorState) -> OrchestratorState:
        """Convert cellar recommendations into a priority-ordered market search plan."""
        try:
            analysis = state.get("cellar_analysis")
            if not analysis:
                state["error"] = "No analysis available to build a search plan"
                return state

            print("\n[Orchestrator] Building priority-ordered search plan...")

            ordered_recommendations = sorted(
                analysis.recommendations,
                key=lambda rec: self._criticality_rank(rec.criticality),
            )

            if not ordered_recommendations:
                state["search_plan"] = None
                state["missing_wine_categories"] = []
                state["needs_market_analysis"] = False
                state["should_call_market_analysis"] = False
                print("\n[Orchestrator] No recommendations available to build a search plan")
                return state

            search_recommendations = []
            for index, recommendation in enumerate(ordered_recommendations, 1):
                search_recommendations.append(
                    RecommendationSearchPlan(
                        title=recommendation.title,
                        criticality=recommendation.criticality,
                        priority_rank=index,
                        should_call_market_analysis=self._should_call_market_analysis(
                            recommendation,
                            index,
                        ),
                        quantity_to_buy=recommendation.quantity_to_buy,
                        criteria=self._build_criteria(recommendation),
                    )
                )

            search_plan = OrchestratorSearchPlan(recommendations=search_recommendations)
            state["search_plan"] = search_plan
            state["missing_wine_categories"] = [
                item.title for item in search_recommendations if item.should_call_market_analysis
            ]
            state["needs_market_analysis"] = any(
                item.should_call_market_analysis for item in search_recommendations
            )
            state["should_call_market_analysis"] = state["needs_market_analysis"]

            print(f"\n[Orchestrator] Prepared {len(search_recommendations)} search items:")
            for item in search_recommendations:
                decision = "call market analysis" if item.should_call_market_analysis else "skip market analysis"
                print(f"  - #{item.priority_rank} {item.title} -> {decision}")

            return state

        except Exception as e:
            state["error"] = f"Search plan generation failed: {str(e)}"
            return state

    async def _run_market_analysis(self, state: OrchestratorState) -> OrchestratorState:
        """Call the market analysis agent for selected recommendations."""
        try:
            search_plan = state.get("search_plan")
            if not search_plan:
                state["market_analysis_results"] = []
                return state

            from api.MarketAnalysisAgent.service import MarketAnalysisService

            results = []
            for item in search_plan.recommendations:
                if not item.should_call_market_analysis:
                    continue
                result = await MarketAnalysisService.analyze_recommendation(
                    criteria=item.criteria.model_dump(),
                    quantity=item.quantity_to_buy,
                    recommendation_title=item.title,
                )
                results.append(result)

            state["market_analysis_results"] = results
            return state
        except Exception as e:
            state["error"] = f"Market analysis failed: {str(e)}"
            return state

    async def run(self) -> OrchestratorState:
        """Execute the orchestrator workflow"""
        try:
            initial_state: OrchestratorState = {
                "needs_market_analysis": False,
                "missing_wine_categories": [],
                "should_call_market_analysis": False,
                "search_plan": None,
                "market_analysis_results": [],
            }
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            print(f"[Orchestrator] Workflow failed: {str(e)}")
            raise
