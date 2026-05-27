"""Wine Cellar Analysis Agent using LangGraph"""

import json
from typing import Any
from uuid import UUID
from apps.api.database.repositories.cellar_repository import CellarRepository
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite
from .state import WineCellarAgentState
from .repository import WineCellarRepository
from .models import (
    CriticalityLevel,
    Recommendation,
    RecommendationPlan,
    WineBuyingAspect,
    WineBuyingParameter,
    WineCellarAnalysis,
)
from pydantic import ValidationError


class WineCellarAgent:
    """Wine Cellar Analysis Agent using LangGraph"""

    def __init__(self, cellar_repo: CellarRepository, user_id: UUID | None = None):
        """Initialize the agent with an existing CellarRepository"""
        self.repository = WineCellarRepository(cellar_repo, user_id=user_id)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(WineCellarAgentState)

        # Add nodes
        workflow.add_node("fetch_data", self._fetch_wine_data)
        workflow.add_node("analyze_diversity", self._analyze_diversity)
        workflow.add_node("analyze_strengths", self._analyze_strengths)
        workflow.add_node("analyze_weaknesses", self._analyze_weaknesses)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("format_output", self._format_output)

        # Add edges
        workflow.add_edge("fetch_data", "analyze_diversity")
        workflow.add_edge("analyze_diversity", "analyze_strengths")
        workflow.add_edge("analyze_strengths", "analyze_weaknesses")
        workflow.add_edge("analyze_weaknesses", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "format_output")
        workflow.add_edge("format_output", END)

        # Set entry point
        workflow.set_entry_point("fetch_data")

        return workflow.compile()

    async def _fetch_wine_data(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Fetch wine data from database"""
        try:
            wines = await self.repository.get_all_wines()
            wine_count = len(wines)
            total_quantity = await self.repository.get_total_quantity()

            wines_by_country = await self.repository.get_wines_by_country()
            wines_by_region = await self.repository.get_wines_by_region()
            wines_by_color = await self.repository.get_wines_by_color()
            wines_by_grape_variety = await self.repository.get_wines_by_grape_variety()

            wines_data = {
                "total_wines": wine_count,
                "total_quantity": total_quantity,
                "wines": wines,
                "by_country": wines_by_country,
                "by_region": wines_by_region,
                "by_color": wines_by_color,
                "by_grape_variety": wines_by_grape_variety,
            }

            state["wines_data"] = wines_data
            return state
        except Exception as e:
            state["error"] = f"Failed to fetch wine data: {str(e)}"
            return state

    async def _analyze_diversity(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Analyze the diversity of the wine cellar"""
        wines_data = state.get("wines_data", {})

        if not wines_data:
            state["error"] = "No wine data available"
            return state

        prompt = f"""Analyze the diversity of this wine cellar and provide insights:

Total Wines: {wines_data.get("total_wines", 0)}

Distribution by Country:
{json.dumps(wines_data.get("by_country", {}), indent=2)}

Distribution by Region:
{json.dumps(wines_data.get("by_region", {}), indent=2)}

Distribution by Color:
{json.dumps(wines_data.get("by_color", {}), indent=2)}

Distribution by Grape Variety:
{json.dumps(wines_data.get("by_grape_variety", {}), indent=2)}

Please analyze:
1. How diverse is this cellar?
2. Are there any dominant categories?
3. Are there any gaps in diversity?
4. What is the overall diversity score (1-10)?"""

        try:
            message = HumanMessage(content=prompt)
            response = await gemini_flash_3_1_lite.ainvoke([message])
            state["diversity_analysis"] = response.content
            return state
        except Exception as e:
            state["error"] = f"Diversity analysis failed: {str(e)}"
            return state

    async def _analyze_strengths(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Analyze strengths of the wine cellar"""
        wines_data = state.get("wines_data", {})
        diversity_analysis = state.get("diversity_analysis", "")

        prompt = f"""Based on this wine cellar data and diversity analysis:

{wines_data}

Previous Analysis:
{diversity_analysis}

Identify the top 3-5 strengths of this wine cellar. Consider:
- Well-represented regions or countries
- Good balance of wine colors or grape varieties
- Unique or valuable selections
- Geographic representation

List each strength as a clear, concise statement."""

        try:
            message = HumanMessage(content=prompt)
            response = await gemini_flash_3_1_lite.ainvoke([message])
            state["strengths_analysis"] = response.content
            return state
        except Exception as e:
            state["error"] = f"Strengths analysis failed: {str(e)}"
            return state

    async def _analyze_weaknesses(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Analyze weaknesses of the wine cellar"""
        wines_data = state.get("wines_data", {})
        diversity_analysis = state.get("diversity_analysis", "")
        strengths_analysis = state.get("strengths_analysis", "")

        prompt = f"""Based on this wine cellar data:

{wines_data}

And the following analyses:
Diversity: {diversity_analysis}
Strengths: {strengths_analysis}

Identify the top 3-5 weaknesses or areas for improvement in this wine cellar. Consider:
- Underrepresented regions or countries
- Lack of specific wine colors or grape varieties
- Geographic gaps
- Imbalances in the collection

List each weakness as a clear, concise statement."""

        try:
            message = HumanMessage(content=prompt)
            response = await gemini_flash_3_1_lite.ainvoke([message])
            state["weaknesses_analysis"] = response.content
            return state
        except Exception as e:
            state["error"] = f"Weaknesses analysis failed: {str(e)}"
            return state

    async def _generate_recommendations(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Generate specific recommendations for the wine cellar"""
        strengths = state.get("strengths_analysis", "")
        weaknesses = state.get("weaknesses_analysis", "")

        allowed_aspects = ", ".join(aspect.value for aspect in WineBuyingAspect)

        prompt = f"""Based on the wine cellar analysis, return a structured recommendation plan.

Strengths:
{strengths}

Weaknesses:
{weaknesses}

Generate 4-6 specific, actionable recommendations to improve this wine cellar.

Each recommendation must include:
- title
- description
- criticality
- price_range
- quantity_to_buy
- parameters
- suggested_action
- estimated_impact

Rules for parameters:
- Each recommendation must propose at least one wine purchase parameter.
- Each parameter.aspect must be one of: {allowed_aspects}
- The target field should be a concise value or range, such as a country, region, price range, alcohol level, colour, tannin level, acidity level, sweetness level, body, grape variety, style, vintage, ageing potential, or food pairing.
- The recommendation must always include a price range expressed as a concise human-readable range such as "15-25 EUR" or "30-45 USD".
- quantity_to_buy must be a positive integer that reflects how many bottles to buy.
- Keep the recommendations practical and varied.
"""

        def _validate_plan(data: Any) -> RecommendationPlan:
            if hasattr(RecommendationPlan, "model_validate"):
                return RecommendationPlan.model_validate(data)
            return RecommendationPlan.parse_obj(data)

        def _extract_json(text: str) -> str | None:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            return text[start : end + 1]

        try:
            structured_llm = gemini_flash_3_1_lite.with_structured_output(RecommendationPlan)
            response = await structured_llm.ainvoke(prompt)
            state["recommendation_plan"] = response
            return state
        except Exception as e:
            last_error = str(e)

        repair_prompt = (
            f"""{prompt}

Return ONLY valid JSON that matches this exact schema and includes all required fields.
Do not include markdown, comments, or extra text.

Schema:
{{
  "recommendations": [
    {{
      "title": "string",
      "description": "string",
      "criticality": "low|medium|high|critical",
      "price_range": "string",
      "quantity_to_buy": 1,
      "parameters": [
        {{
          "aspect": "country|region|sub_region|price_range|alcohol_level|colour|tannin|acidity|sweetness|body|grape_variety|style|vintage|ageing_potential|food_pairing",
          "target": "string",
          "rationale": "string"
        }}
      ],
      "suggested_action": "string",
      "estimated_impact": "string"
    }}
  ]
}}

Previous error: {last_error}
"""
        )

        for _ in range(2):
            try:
                message = HumanMessage(content=repair_prompt)
                response = await gemini_flash_3_1_lite.ainvoke([message])
                raw_text = response.content if hasattr(response, "content") else str(response)
                json_text = _extract_json(raw_text)
                if not json_text:
                    raise ValueError("No JSON object found in model response")
                data = json.loads(json_text)
                state["recommendation_plan"] = _validate_plan(data)
                return state
            except Exception as e:
                last_error = str(e)
                repair_prompt = repair_prompt.rsplit("Previous error:", 1)[0] + f"Previous error: {last_error}\n"

        # Fallback to a valid default plan instead of failing the workflow
        state["recommendation_plan"] = RecommendationPlan(
            recommendations=self._default_recommendations()
        )
        return state

    async def _format_output(self, state: WineCellarAgentState) -> WineCellarAgentState:
        """Format the final structured output"""
        wines_data = state.get("wines_data", {})
        strengths_analysis = state.get("strengths_analysis", "") or ""
        weaknesses_analysis = state.get("weaknesses_analysis", "") or ""
        recommendation_plan = state.get("recommendation_plan")

        # Normalize various possible response types (str, list, dict) to text
        def _to_text(val):
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                parts = []
                for el in val:
                    if isinstance(el, str):
                        parts.append(el)
                    else:
                        try:
                            parts.append(json.dumps(el))
                        except Exception:
                            parts.append(str(el))
                return "\n".join(parts)
            if isinstance(val, dict):
                try:
                    return json.dumps(val)
                except Exception:
                    return str(val)
            return str(val)

        strengths_analysis = _to_text(strengths_analysis)
        weaknesses_analysis = _to_text(weaknesses_analysis)

        # Parse strengths from analysis
        strengths_list = [
            s.strip() for s in strengths_analysis.split("\n") if s.strip() and not s.startswith("#")
        ]
        weaknesses_list = [
            w.strip()
            for w in weaknesses_analysis.split("\n")
            if w.strip() and not w.startswith("#")
        ]

        recommendations = (
            recommendation_plan.recommendations
            if recommendation_plan
            else self._default_recommendations()
        )

        # Create diversity metrics
        diversity_metrics = {
            "countries": len(wines_data.get("by_country", {})),
            "regions": len(wines_data.get("by_region", {})),
            "wine_colors": len(wines_data.get("by_color", {})),
            "grape_varieties": len(wines_data.get("by_grape_variety", {})),
            "total_quantity": wines_data.get("total_quantity", 0),
            "distribution_by_country": wines_data.get("by_country", {}),
            "distribution_by_color": wines_data.get("by_color", {}),
            "distribution_by_grape_variety": wines_data.get("by_grape_variety", {}),
        }

        # Generate overall assessment
        overall_assessment = f"""This wine cellar contains {wines_data.get("total_wines", 0)} wines representing
        {len(wines_data.get("by_country", {}))} countries and {len(wines_data.get("by_region", {}))} regions.
        The collection demonstrates a {self._calculate_diversity_level(wines_data)} level of diversity."""

        total_quantity = wines_data.get("total_quantity", 0)
        if wines_data.get("total_wines", 0) > 0:
            avg_per_entry = round(total_quantity / wines_data.get("total_wines", 1), 2)
            quantity_observation = (
                f"The user has {total_quantity} total bottles across {wines_data.get('total_wines', 0)} entries "
                f"(avg {avg_per_entry} per entry)."
            )
        else:
            quantity_observation = "The user has no bottles recorded in the cellar."

        summary = f"""{quantity_observation} The cellar shows {len(strengths_list)} key strengths and has
        {len(weaknesses_list)} areas for improvement. {len(recommendations)} actionable recommendations
        have been identified."""

        try:
            analysis_result = WineCellarAnalysis(
                total_wines=wines_data.get("total_wines", 0),
                quantity_observation=quantity_observation,
                diversity_metrics=diversity_metrics,
                strengths=strengths_list[:5],
                weaknesses=weaknesses_list[:5],
                recommendations=recommendations,
                overall_assessment=overall_assessment,
                summary=summary,
            )
            state["analysis_result"] = analysis_result
            return state
        except ValidationError as e:
            state["error"] = f"Failed to create structured output: {str(e)}"
            return state
        except Exception as e:
            state["error"] = f"Output formatting failed: {str(e)}"
            return state

    def _default_recommendations(self) -> list[Recommendation]:
        """Fallback recommendations used when structured output cannot be produced"""

        return [
            Recommendation(
                title="Expand Geographic Diversity",
                description="The cellar would benefit from expanding its geographic representation.",
                criticality=CriticalityLevel.MEDIUM,
                price_range="20-35 EUR",
                quantity_to_buy=6,
                parameters=[
                    WineBuyingParameter(
                        aspect=WineBuyingAspect.COUNTRY,
                        target="Underrepresented countries",
                        rationale="Broader geographic coverage improves cellar balance",
                    ),
                    WineBuyingParameter(
                        aspect=WineBuyingAspect.REGION,
                        target="Underrepresented wine regions",
                        rationale="Region-level diversity adds depth and variety",
                    ),
                ],
                suggested_action="Acquire wines from underrepresented regions",
                estimated_impact="Improved global representation and tasting experiences",
            ),
            Recommendation(
                title="Balance Wine Styles",
                description="Consider balancing the styles and profiles in your collection.",
                criticality=CriticalityLevel.MEDIUM,
                price_range="15-30 EUR",
                quantity_to_buy=4,
                parameters=[
                    WineBuyingParameter(
                        aspect=WineBuyingAspect.COLOUR,
                        target="A colour not currently dominant in the cellar",
                        rationale="Colour balance makes the cellar more versatile",
                    ),
                    WineBuyingParameter(
                        aspect=WineBuyingAspect.PRICE_RANGE,
                        target="Mid-range bottles that complement the existing collection",
                        rationale="A balanced price range improves flexibility and value",
                    ),
                ],
                suggested_action="Review current style distribution and buy complementary wines",
                estimated_impact="More versatile cellar suitable for various occasions",
            ),
        ]

    def _calculate_diversity_level(self, wines_data: dict[str, Any]) -> str:
        """Calculate diversity level based on metrics"""
        num_countries = len(wines_data.get("by_country", {}))
        num_varieties = len(wines_data.get("by_grape_variety", {}))
        num_colors = len(wines_data.get("by_color", {}))
        total_wines = wines_data.get("total_wines", 0)

        diversity_score = (
            (num_countries * 0.35)
            + (num_varieties * 0.35)
            + (num_colors * 0.1)
            + min(total_wines / 50, 10) * 0.2
        )

        if diversity_score >= 8:
            return "excellent"
        elif diversity_score >= 6:
            return "good"
        elif diversity_score >= 4:
            return "moderate"
        else:
            return "limited"

    async def analyze(self) -> WineCellarAnalysis:
        """Run the complete wine cellar analysis"""
        # Invoke the graph asynchronously
        result = await self.graph.ainvoke({})
        if result.get("error"):
            raise Exception(result["error"])
        analysis = result.get("analysis_result")
        if not analysis:
            raise Exception("No analysis result generated")
        return analysis
