"""Sales Analysis Agent using LangGraph."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite
from api.SalesAnalysisAgent.models import (
    CriticalityLevel,
    RecommendationType,
    SalesAnalysisFocus,
    SalesAnalysisQuery,
    SalesAnalysisResult,
    SalesRecommendation,
    SalesRecommendationPlan,
)
from api.SalesAnalysisAgent.repository import SalesAnalysisRepository
from api.SalesAnalysisAgent.state import SalesAnalysisAgentState
from ..database.repositories.cellar_repository import CellarRepository


class SalesAnalysisAgent:
    """Sales Analysis Agent using LangGraph."""

    def __init__(
        self,
        cellar_repo: CellarRepository,
        user_id: UUID | None = None,
        lookback_days: int = 30,
    ):
        self.repository = SalesAnalysisRepository(cellar_repo, user_id=user_id)
        self.lookback_days = max(7, lookback_days)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SalesAnalysisAgentState)

        workflow.add_node("parse_focus", self._parse_focus)
        workflow.add_node("fetch_data", self._fetch_data)
        workflow.add_node("analyze_trends", self._analyze_trends)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("format_output", self._format_output)

        workflow.add_edge("parse_focus", "fetch_data")
        workflow.add_edge("fetch_data", "analyze_trends")
        workflow.add_edge("analyze_trends", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "format_output")
        workflow.add_edge("format_output", END)

        workflow.set_entry_point("parse_focus")

        return workflow.compile()

    async def _parse_focus(self, state: SalesAnalysisAgentState) -> SalesAnalysisAgentState:
        focus_input = state.get("focus_input")
        if not focus_input:
            state["focus"] = SalesAnalysisFocus()
            return state

        if isinstance(focus_input, SalesAnalysisFocus):
            focus = focus_input
        else:
            focus = SalesAnalysisFocus(**focus_input)

        if focus.query and not (focus.wine_name or focus.wine_type or focus.price_range):
            prompt = (
                "Extract a sales analysis focus from this request. "
                "Return wine_name, wine_type, and price_range when present. "
                "Leave fields null when not stated.\n\n"
                f"Request: {focus.query}"
            )
            try:
                structured_llm = gemini_flash_3_1_lite.with_structured_output(SalesAnalysisQuery)
                parsed = await structured_llm.ainvoke(prompt)
                focus = focus.model_copy(update=parsed.model_dump(exclude_none=True))
            except Exception:
                pass

        if focus.wine_name and not focus.wine_id:
            matched = await self.repository.resolve_wine_by_name(focus.wine_name)
            if matched:
                focus.wine_id = matched.id
                focus.wine_name = matched.name

        state["focus"] = focus
        return state

    async def _fetch_data(self, state: SalesAnalysisAgentState) -> SalesAnalysisAgentState:
        focus = state.get("focus")
        try:
            summary = await self.repository.get_sales_stock_summary(
                focus=focus,
                lookback_days=self.lookback_days,
            )
            movers = await self.repository.get_sales_movers()
            state["sales_data"] = {
                "summary": summary,
                "movers": movers,
                "focus": focus.model_dump() if focus else {},
            }
            return state
        except Exception as e:
            state["error"] = f"Failed to fetch sales data: {str(e)}"
            return state

    async def _analyze_trends(self, state: SalesAnalysisAgentState) -> SalesAnalysisAgentState:
        sales_data = state.get("sales_data", {})
        if not sales_data:
            state["error"] = "No sales data available"
            return state

        prompt = f"""Analyze sales vs stock trends and provide concise observations.

Sales summary:
{json.dumps(sales_data.get('summary', {}), indent=2)}

Movers:
{json.dumps(sales_data.get('movers', {}), indent=2)}

Focus:
{json.dumps(sales_data.get('focus', {}), indent=2)}

Return 3-6 bullet-point observations that describe:
- Whether sales are keeping up with stock
- Recent sales momentum (up/down/flat)
- Any fast movers or slow movers worth noting
- Implications for stocking or pricing (recommendation-only language)
"""

        try:
            message = HumanMessage(content=prompt)
            response = await gemini_flash_3_1_lite.ainvoke([message])
            state["trend_analysis"] = response.content
            return state
        except Exception as e:
            state["error"] = f"Trend analysis failed: {str(e)}"
            return state

    async def _generate_recommendations(self, state: SalesAnalysisAgentState) -> SalesAnalysisAgentState:
        trend_analysis = state.get("trend_analysis", "")
        summary = state.get("sales_data", {}).get("summary", {})
        focus = state.get("sales_data", {}).get("focus", {})

        prompt = f"""Generate 3-5 sales recommendations based on this analysis.

Trend analysis:
{trend_analysis}

Sales summary:
{json.dumps(summary, indent=2)}

Focus:
{json.dumps(focus, indent=2)}

Rules:
- Recommendations must be advisory only (use language like "recommend", "consider").
- Include a mix of recommendations: buy more stock for strong sellers, reduce stock or adjust price for slow movers, or monitor.
- Each recommendation must include title, description, criticality, recommendation_type, target, suggested_action, evidence, expected_impact.
"""

        try:
            structured_llm = gemini_flash_3_1_lite.with_structured_output(SalesRecommendationPlan)
            response = await structured_llm.ainvoke(prompt)
            state["recommendation_plan"] = response
            return state
        except Exception as e:
            state["error"] = f"Recommendations generation failed: {str(e)}"
            return state

    async def _format_output(self, state: SalesAnalysisAgentState) -> SalesAnalysisAgentState:
        sales_data = state.get("sales_data", {})
        trend_analysis = state.get("trend_analysis", "") or ""
        recommendation_plan = state.get("recommendation_plan")

        def _to_text(val: Any) -> str:
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                return "\n".join(str(item) for item in val)
            if isinstance(val, dict):
                try:
                    return json.dumps(val)
                except Exception:
                    return str(val)
            return str(val)

        trend_text = _to_text(trend_analysis)
        trend_observations = [
            line.strip("- ")
            for line in trend_text.split("\n")
            if line.strip()
        ]

        recommendations = (
            recommendation_plan.recommendations
            if recommendation_plan
            else self._default_recommendations()
        )

        summary = sales_data.get("summary", {})
        focus = sales_data.get("focus", {})
        movers = sales_data.get("movers", {})

        overall_assessment = (
            f"Sales trend is {summary.get('sales_trend', 'flat')} with "
            f"sell-through rate {summary.get('sell_through_rate', 0)} over the last "
            f"{summary.get('lookback_days', self.lookback_days)} days."
        )

        summary_text = (
            f"{summary.get('sales', {}).get('recent', 0)} sales in the recent period vs "
            f"{summary.get('stock', {}).get('current', 0)} bottles in stock. "
            f"Generated {len(recommendations)} recommendations for {summary.get('focus_label', 'all wines')}."
        )

        try:
            analysis_result = SalesAnalysisResult(
                focus={
                    "label": summary.get("focus_label", "All wines"),
                    "details": focus,
                },
                stock_metrics=summary.get("stock", {}),
                sales_metrics={
                    **summary.get("sales", {}),
                    "trend": summary.get("sales_trend"),
                    "change_pct": summary.get("sales_change_pct"),
                    "sell_through_rate": summary.get("sell_through_rate"),
                    "lookback_days": summary.get("lookback_days"),
                },
                movers={
                    "fast_movers": movers.get("fast_movers", []),
                    "slow_movers": movers.get("slow_movers", []),
                },
                trend_observations=trend_observations[:6],
                recommendations=recommendations,
                overall_assessment=overall_assessment,
                summary=summary_text,
            )
            state["analysis_result"] = analysis_result
            return state
        except ValidationError as e:
            state["error"] = f"Failed to create structured output: {str(e)}"
            return state
        except Exception as e:
            state["error"] = f"Output formatting failed: {str(e)}"
            return state

    def _default_recommendations(self) -> list[SalesRecommendation]:
        return [
            SalesRecommendation(
                title="Reinforce top sellers",
                description="Strong sellers may benefit from modest stock increases to avoid missed sales.",
                criticality=CriticalityLevel.MEDIUM,
                recommendation_type=RecommendationType.INCREASE_STOCK,
                target="Fast movers",
                suggested_action="Consider increasing stock levels for the top selling wines.",
                evidence="Fast movers show consistent sales against limited stock.",
                expected_impact="Reduced stockouts and steadier sales coverage.",
            ),
            SalesRecommendation(
                title="Reduce exposure on slow movers",
                description="Slow-moving wines may need leaner inventory or a pricing review.",
                criticality=CriticalityLevel.MEDIUM,
                recommendation_type=RecommendationType.REDUCE_STOCK,
                target="Slow movers",
                suggested_action="Consider lowering reorder quantities and reviewing pricing strategy.",
                evidence="Slow movers show limited sales despite available stock.",
                expected_impact="Lower carrying costs and improved cash efficiency.",
            ),
        ]

    async def analyze(self, focus: SalesAnalysisFocus | dict | None = None) -> SalesAnalysisResult:
        """Run the complete sales analysis."""
        result = await self.graph.ainvoke({"focus_input": focus})
        if result.get("error"):
            raise Exception(result["error"])
        analysis = result.get("analysis_result")
        if not analysis:
            raise Exception("No analysis result generated")
        return analysis
