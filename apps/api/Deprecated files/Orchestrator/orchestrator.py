"""Orchestrator Agent for wine cellar management"""

from langgraph.graph import StateGraph, END
from .state import OrchestratorState
from .event_manager import event_manager
from .events import AnalysisRunEvent, WineSoldEvent
import uuid
from uuid import UUID
from apps.api.database.repositories.cellar_repository import CellarRepository
from .models import MarketSearchCriteria, RecommendationSearchPlan, OrchestratorSearchPlan
from apps.api.WineCellarAgent.models import CriticalityLevel, WineBuyingAspect, Recommendation
from apps.api.agents.event_bus import event_bus, AgentEvent
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.database.repositories.recommendations_repository import RecommendationRepository
from apps.api.MarketAnalysisAgent.models import MarketAnalysisResult


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
        workflow.add_node("persist_recommendations", self._persist_recommendations)

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
        workflow.add_edge("run_market_analysis", "persist_recommendations")
        workflow.add_edge("persist_recommendations", END)

        return workflow.compile()

    async def _decide_entry_point(self, state: OrchestratorState):
        """
        Checks for a trigger event and decides whether to start the analysis.
        """
        print("[Orchestrator] Checking for trigger event...")
        if state.get("trigger_event"):
            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="trigger_detected",
                    message=f"Trigger: {state['trigger_event']}",
                )
            )
            return state

        last_event = event_manager.get_last_event()
        if last_event and isinstance(last_event, WineSoldEvent):
            print(f"[Orchestrator] Detected '{last_event.event_type}' event. Triggering analysis.")
            state["trigger_event"] = last_event.event_type
            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="trigger_detected",
                    message=f"Trigger: {last_event.event_type}",
                )
            )
        else:
            print("[Orchestrator] No trigger event detected.")
            state["trigger_event"] = None
            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="idle",
                    message="No trigger event detected",
                )
            )
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
        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="analysis_started",
                message="Cellar analysis started",
            )
        )
        from WineCellarAgent.service import WineCellarAnalysisService

        service = WineCellarAnalysisService()
        analysis = await service.analyze_cellar(self.cellar_repo, user_id=self.user_id)
        state["cellar_analysis"] = analysis

        # Add analysis event
        analysis_id = str(uuid.uuid4())
        event = AnalysisRunEvent(agent_name="WineCellarAnalysisAgent", analysis_id=analysis_id)
        event_manager.add_event(event)
        state["analysis_id"] = analysis_id

        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type="analysis_completed",
                message=f"Cellar analysis completed ({analysis_id})",
            )
        )
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

    def _should_call_market_analysis(
        self, recommendation: Recommendation, priority_rank: int
    ) -> bool:
        """Decide whether a recommendation should trigger market analysis."""
        return True

    def _build_pertinence_message(self, criticality: CriticalityLevel, fit_score: float) -> str:
        """Explain how criticality impacts buying pertinence."""
        criticality_label = criticality.value
        if fit_score >= 0.7:
            fit_note = "strong match"
        elif fit_score >= 0.4:
            fit_note = "moderate match"
        else:
            fit_note = "weak match"

        return f"Criticality is {criticality_label}; market fit is a {fit_note}. "

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
            elif (
                parameter.aspect == WineBuyingAspect.SUB_REGION
                and "sub_region" not in criteria_values
            ):
                criteria_values["sub_region"] = parameter.target
            elif (
                parameter.aspect == WineBuyingAspect.GRAPE_VARIETY
                and "grape_variety" not in criteria_values
            ):
                criteria_values["grape_variety"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.STYLE and "style" not in criteria_values:
                criteria_values["style"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.VINTAGE and "vintage" not in criteria_values:
                criteria_values["vintage"] = parameter.target
            elif (
                parameter.aspect == WineBuyingAspect.ALCOHOL_LEVEL
                and "alcohol_level" not in criteria_values
            ):
                criteria_values["alcohol_level"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.TANNIN and "tannin" not in criteria_values:
                criteria_values["tannin"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.ACIDITY and "acidity" not in criteria_values:
                criteria_values["acidity"] = parameter.target
            elif (
                parameter.aspect == WineBuyingAspect.SWEETNESS
                and "sweetness" not in criteria_values
            ):
                criteria_values["sweetness"] = parameter.target
            elif parameter.aspect == WineBuyingAspect.BODY and "body" not in criteria_values:
                criteria_values["body"] = parameter.target
            elif (
                parameter.aspect == WineBuyingAspect.AGEING_POTENTIAL
                and "ageing_potential" not in criteria_values
            ):
                criteria_values["ageing_potential"] = parameter.target
            elif (
                parameter.aspect == WineBuyingAspect.FOOD_PAIRING
                and "food_pairing" not in criteria_values
            ):
                criteria_values["food_pairing"] = parameter.target

        return MarketSearchCriteria(**criteria_values)

    def _build_recommendation_reason(self, result: MarketAnalysisResult) -> str:
        """Create a concise reason string for a persisted recommendation."""
        fit_notes = "; ".join(result.fit_notes) if result.fit_notes else "No fit notes provided"
        pertinence = result.buying_pertinence or "Buying pertinence not specified"
        return f"{result.recommendation_title}. Fit notes: {fit_notes}. {pertinence}"

    def _resolve_market_price(self, result: MarketAnalysisResult) -> float:
        """Prefer per-bottle price, fall back to total price / quantity."""
        if result.price_per_bottle is not None:
            return result.price_per_bottle
        if result.total_price is not None and result.quantity > 0:
            return result.total_price / result.quantity
        return 0.0

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
            state["missing_wine_categories"] = [item.title for item in search_recommendations]
            state["needs_market_analysis"] = True
            state["should_call_market_analysis"] = True

            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="market_analysis_decision",
                    message=(
                        "Market analysis needed"
                        if state["needs_market_analysis"]
                        else "Market analysis not needed"
                    ),
                )
            )

            print(f"\n[Orchestrator] Prepared {len(search_recommendations)} search items:")
            for item in search_recommendations:
                decision = (
                    "call market analysis"
                    if item.should_call_market_analysis
                    else "skip market analysis"
                )
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

            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="market_analysis_started",
                    message="Market analysis started",
                )
            )

            from MarketAnalysisAgent.service import MarketAnalysisService

            results = []
            for item in search_plan.recommendations:
                result = await MarketAnalysisService.analyze_recommendation(
                    criteria=item.criteria.model_dump(),
                    quantity=item.quantity_to_buy,
                    recommendation_title=item.title,
                )
                results.append(
                    result.model_copy(
                        update={
                            "recommendation_criticality": item.criticality.value,
                            "buying_pertinence": self._build_pertinence_message(
                                item.criticality,
                                result.fit_score,
                            ),
                        }
                    )
                )

            state["market_analysis_results"] = results
            await event_bus.publish(
                AgentEvent(
                    source="orchestrator",
                    type="market_analysis_completed",
                    message=f"Market analysis completed ({len(results)} results)",
                )
            )
            return state
        except Exception as e:
            state["error"] = f"Market analysis failed: {str(e)}"
            return state

    async def _persist_recommendations(self, state: OrchestratorState) -> OrchestratorState:
        """Persist market analysis recommendations to the database."""
        results = state.get("market_analysis_results") or []
        if not results:
            state["recommendations_saved"] = 0
            return state

        try:
            async with AsyncSessionLocal() as session:
                user_id = self.user_id or await get_demo_user_id(session)
                repo = RecommendationRepository(session, read_only=False)
                for result in results:
                    await repo.create(
                        user_id=user_id,
                        wine_id=result.wine_id,
                        quantity=result.quantity,
                        market_price=self._resolve_market_price(result),
                        priority_score=result.fit_score,
                        recommendation_reason=self._build_recommendation_reason(result),
                    )
                state["recommendations_saved"] = len(results)
            return state
        except Exception as e:
            state["error"] = f"Recommendation persistence failed: {str(e)}"
            return state

    async def run(self, trigger_event: str | None = None) -> OrchestratorState:
        """Execute the orchestrator workflow"""
        try:
            initial_state: OrchestratorState = {
                "trigger_event": trigger_event,
                "needs_market_analysis": False,
                "missing_wine_categories": [],
                "should_call_market_analysis": False,
                "search_plan": None,
                "market_analysis_results": [],
                "recommendations_saved": 0,
            }
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            print(f"[Orchestrator] Workflow failed: {str(e)}")
            raise
