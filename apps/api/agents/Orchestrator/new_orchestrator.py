from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from datetime import datetime, timezone
import json
from .state import OrchestratorState
import uuid
from uuid import UUID
from apps.api.database.repositories.cellar_repository import CellarRepository
from apps.api.agents.Orchestrator.checkpointer import get_checkpointer
from apps.api.agents.cellarAudit.agent import run_inventory_audit
from apps.api.agents.subagents.menu_generator import make_menu_generator_tool
from apps.api.agents.subagents.market_research import make_market_research_tool
from apps.api.agents.salesAnalyser.agent import run_sales_analysis
from apps.api.agents.Orchestrator.orchestrator_router import orchestrator_router
from apps.api.events.bus import AgentEvent, event_bus
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.database.repositories.cellar_repository import CellarRepository
from apps.api.WineCardAgent.service import WineCardService
from apps.api.WineCardAgent.trigger_service import WineCardTriggerService
from apps.api.WineCardAgent.models import TriggerReason, Season, VatCountry

class Orchestrator:
    """Orchestrator for wine cellar analysis and market research workflows"""

    def __init__(self, cellar_repo: CellarRepository, user_id: UUID | None = None, checkpointer=None):
        """Initialize the orchestrator"""
        if cellar_repo is None:
            raise ValueError("cellar_repo is required")
        self.cellar_repo = cellar_repo
        self.user_id = user_id
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer) -> CompiledStateGraph:
        workflow = StateGraph(OrchestratorState)

        workflow.add_node("event_listener", self._event_listener)
        workflow.add_node("orchestrator_router", self._run_router)
        workflow.add_node("analyze_cellar", self._analyze_cellar)
        workflow.add_node("run_market_analysis", self._run_market_analysis)
        workflow.add_node("persist_recommendations", self._persist_recommendations)
        workflow.add_node("sales_analysis", self._run_sales_analysis)
        workflow.add_node("update_menu", self._update_menu)

        workflow.set_entry_point("event_listener")
        workflow.add_edge("analyze_cellar", "run_market_analysis")
        workflow.add_edge("run_market_analysis", "orchestrator_router")
        workflow.add_edge("sales_analysis", "orchestrator_router")
        workflow.add_conditional_edges("orchestrator_router", self.route, {
            "sales_analysis": "sales_analysis",
            "run_market_analysis": "run_market_analysis",
            "analyze_cellar": "analyze_cellar",
            "persist_recommendations": "persist_recommendations"
        })
        workflow.add_conditional_edges("event_listener", self.event_analysis, {"orchestrator_router": "orchestrator_router",
                                                                               "update_menu": "update_menu"})
        workflow.add_edge("persist_recommendations", END)
        workflow.add_edge("update_menu", END)

        return workflow.compile(checkpointer=checkpointer)


    async def _event_listener(self, state: OrchestratorState) -> dict:
        return {}

    async def _run_router(self, state: OrchestratorState) -> dict:
        # Call the router function and collect state updates
        import copy
        state_copy = copy.deepcopy(state)
        # Note: the router mutates the dict directly right now and returns the next node
        next_node = await orchestrator_router(str(self.user_id), state_copy)

        # We return the mutated state to LangGraph to apply the updates
        updates = {}
        for k, v in state_copy.items():
            if k not in state or state.get(k) != v:
                updates[k] = v
        return updates

    async def _publish_event(self, event_type: str, message: str) -> None:
        await event_bus.publish(
            AgentEvent(
                source="orchestrator",
                type=event_type,
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )


    async def _analyze_cellar(self, state: OrchestratorState) -> dict:
        try:
            await self._publish_event(
                "action",
                f"Starting cellar analysis for user {self.user_id}.",
            )
            query = state.get("analysis_query") or "Analyze the current cellar state and flag any concerns."
            analysis = await run_inventory_audit(str(self.user_id), query)
            await self._publish_event(
                "observation",
                f"Cellar analysis completed successfully : {analysis.summary}",
            )
        except Exception as e:
            await self._publish_event("alert", f"Error: {e}")
            return {'error': str(e)}
        recommendations = analysis.recommendations or []
        recommendations_json = json.dumps(
            [rec.model_dump() for rec in recommendations],
            ensure_ascii=True,
        )
        return {
            "cellar_analysis": recommendations,
            "analysis_query": recommendations_json,
        }

    async def _run_market_analysis(self, state: OrchestratorState) -> dict:
        try:
            await self._publish_event(
                "action",
                f"Starting market analysis for user {self.user_id}.",
            )
            market_analysis_started_at = datetime.now(timezone.utc)
            query = state.get("analysis_query") or ""
            run_market = make_market_research_tool(str(self.user_id))
            result = await run_market.ainvoke({"query": query})
            await self._publish_event(
                "observation",
                "Market analysis completed successfully.",
            )
        except Exception as e:
            await self._publish_event("alert", f"Error: {e}")
            return {'error': str(e)}
        return {
            'market_analysis': result,
            'market_analysis_started_at': market_analysis_started_at.isoformat(),
        }

    async def _persist_recommendations(self, state: OrchestratorState) -> dict:
        saved = 0
        try:
            await self._publish_event(
                "action",
                "Persisting validated recommendations.",
            )
            # Recommendations are already written to the DB by the save_recommendation
            # tool inside the market research subagent. We just count how many were
            # created during this run by comparing against the run start timestamp.
            started_at_raw = state.get("market_analysis_started_at")
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select, func
                from apps.api.database.models.recommendations import Recommendation as RecommendationModel
                user_id = self.user_id or await get_demo_user_id(session)
                if started_at_raw:
                    from datetime import datetime, timezone
                    started_at = datetime.fromisoformat(started_at_raw)
                    result = await session.execute(
                        select(func.count(RecommendationModel.id)).where(
                            RecommendationModel.user_id == user_id,
                            RecommendationModel.created_at >= started_at,
                        )
                    )
                    saved = int(result.scalar() or 0)
            await self._publish_event(
                "final",
                f"Persisted {saved} recommendation(s).",
            )
        except Exception as e:
            await self._publish_event("alert", f"Error: {e}")
            return {'error': str(e)}
        return {'recommendations_saved': saved}

    async def _run_sales_analysis(self, state: OrchestratorState) -> dict:
        try:
            await self._publish_event(
                "action",
                "Starting sales analysis.",
            )
            query = state.get("analysis_query") or ""
            result = await run_sales_analysis(str(self.user_id), query)
            await self._publish_event(
                "observation",
                "Sales analysis completed successfully.",
            )
        except Exception as e:
            await self._publish_event("alert", f"Error: {e}")
            return {'error': str(e)}
        return {'sales_analysis': result}




    @staticmethod
    def _print_graph(workflow: CompiledStateGraph):

        from IPython.display import Image, display

        png_data = workflow.get_graph().draw_mermaid_png()

        with open("graph.png", "wb") as f:
            f.write(Image(png_data))


        print(workflow.get_graph().print_ascii())


    def route(self, state: OrchestratorState) -> str:
        return state.get("next_node", "persist_recommendations")

    def event_analysis(self, state: OrchestratorState):
        destinations = []
        trigger_event = state.get("trigger_event")
        event_type = trigger_event
        if hasattr(trigger_event, "event_type"):
            event_type = trigger_event.event_type

        if event_type == "wine_sold":
            destinations.append("update_menu")

        if event_type in {"wine_sold", "analysis", "analysis_run"}:
            destinations.append("orchestrator_router")

        return destinations or "orchestrator_router"


    async def _update_menu(self, state: OrchestratorState) -> dict:
        try:
            reason = TriggerReason.WINE_SOLD

            await self._publish_event("action", f"Running WineCard refresh ({reason.value}).")

            report = await WineCardTriggerService.run_once(
                reason=reason,
                season=Season.WINTER,      # ou récupéré depuis state/config
                vat_country=VatCountry.LU, # ou récupéré depuis state/config
                min_stock_threshold=2,
            )

            await self._publish_event(
                "observation",
                f"WineCard regenerated. low_stock_count={report.low_stock_count}, "
                f"refresh={report.should_refresh_menu}"
            )

            return {
                "menu_update_report": report.model_dump(),
            }

        except Exception as e:
            await self._publish_event("alert", f"WineCard update failed: {e}")
            return {"error": str(e)}
