"""
Inventory Audit Subagent
========================
Focused on cellar state analysis: bottle counts, regional balance, low-stock warnings.
Returns a WineCellarAnalysis so it shares a common output contract with WineCellarAgent.
"""

import json
from typing import Any

from apps.api.agents.subagents.utils import run_subagent
from apps.api.agents.WineCellarAgent.models import (
    CriticalityLevel,
    Recommendation,
    RecommendationPlan,
    WineBuyingAspect,
    WineBuyingParameter,
    WineCellarAnalysis,
)
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from apps.api.events.bus import AgentEvent, event_bus
from apps.api.llm_models.gemini_flash_3_1_lite import gemini_flash_3_1_lite
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from sqlalchemy import func, select

from .tools import make_tools

LOW_STOCK_THRESHOLD = 3
MAX_EVENT_MESSAGE_LEN = 2000

INVENTORY_AUDIT_SYSTEM_PROMPT = """You are the Inventory Audit agent for Chimerai, a restaurant sommelier system.

Your sole responsibility is to analyze the current state of the wine cellar and provide insights.

You have four tools:
- get_all_wines: list all wines in the cellar with quantity of each
- get_wines_by_field(field, value): filter wines by a specific field and value (e.g. color='red', country='France', region='Bordeaux', grape_variety='Chardonnay'). Returns detailed wine list.
- flag_low_stock: list of wines at 3 bottles or fewer
- get_wine_count: total bottle count in the cellar

Your task:
1. Examine the cellar data provided to you
2. Write a clear, concise summary of the cellar state and any issues
3. Identify diversity gaps (missing categories)
4. Flag any concerns about low-stock wines

Be analytical but concise. Focus on actionable insights.
"""


def create_inventory_audit_agent(user_id: str):
    tools = make_tools(user_id)
    return create_agent(
        model=gemini_flash_3_1_lite,
        tools=tools,
        system_prompt=INVENTORY_AUDIT_SYSTEM_PROMPT,
    )


async def _publish_inventory_event(event_type: str, message: str) -> None:
    if len(message) > MAX_EVENT_MESSAGE_LEN:
        message = message[:MAX_EVENT_MESSAGE_LEN] + "..."
    await event_bus.publish(
        AgentEvent(
            source="CellarAnalysisAgent",
            type=event_type,
            message=message,
        )
    )


async def _fetch_cellar_data(user_id: str) -> dict[str, Any]:
    """
    Fetch structured cellar data directly from the DB.
    Mirrors the logic in get_cellar_overview but returns raw dicts instead of text.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Wine.name,
                Wine.country,
                Wine.region,
                Wine.color,
                Wine.grape_variety,
                func.count(Cellar.id).label("bottle_count"),
            )
            .join(Cellar, Cellar.wine_id == Wine.id)
            .where(
                Cellar.user_id == user_id,
                Cellar.status == BottleStatus.IN_CELLAR,
            )
            .group_by(Wine.id, Wine.name, Wine.country, Wine.region, Wine.color, Wine.grape_variety)
        )
        rows = result.all()

    if not rows:
        return {
            "total_wines": 0,
            "total_quantity": 0,
            "by_color": {},
            "by_country": {},
            "by_region": {},
            "by_grape_variety": {},
            "low_stock_wines": [],
            "diversity_gaps": [],
        }

    total_quantity = sum(row.bottle_count for row in rows)
    total_wines = len(rows)

    by_color: dict[str, int] = {}
    by_country: dict[str, int] = {}
    by_region: dict[str, int] = {}
    by_grape_variety: dict[str, int] = {}
    low_stock_wines: list[str] = []
    colors_seen: set[str] = set()

    for row in rows:
        by_color[row.color] = by_color.get(row.color, 0) + row.bottle_count
        by_country[row.country] = by_country.get(row.country, 0) + row.bottle_count
        by_region[row.region] = by_region.get(row.region, 0) + row.bottle_count
        by_grape_variety[row.grape_variety] = by_grape_variety.get(row.grape_variety, 0) + row.bottle_count
        colors_seen.add(row.color.lower() if row.color else "")
        if row.bottle_count <= LOW_STOCK_THRESHOLD:
            low_stock_wines.append(f"{row.name}: {row.bottle_count} bottle(s)")

    expected_colors = {"red", "white", "rosé", "sparkling", "dessert", "fortified"}
    diversity_gaps = sorted(expected_colors - colors_seen)

    return {
        "total_wines": total_wines,
        "total_quantity": total_quantity,
        "by_color": by_color,
        "by_country": by_country,
        "by_region": by_region,
        "by_grape_variety": by_grape_variety,
        "low_stock_wines": low_stock_wines,
        "diversity_gaps": diversity_gaps,
    }


def _calculate_diversity_level(data: dict[str, Any]) -> str:
    num_countries = len(data.get("by_country", {}))
    num_varieties = len(data.get("by_grape_variety", {}))
    num_colors = len(data.get("by_color", {}))
    total_quantity = data.get("total_quantity", 0)

    score = (
        (num_countries * 0.35)
        + (num_varieties * 0.35)
        + (num_colors * 0.1)
        + min(total_quantity / 50, 10) * 0.2
    )

    if score >= 8:
        return "excellent"
    elif score >= 6:
        return "good"
    elif score >= 4:
        return "moderate"
    return "limited"


def _default_recommendations() -> list[Recommendation]:
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
            ],
            suggested_action="Review current style distribution and buy complementary wines",
            estimated_impact="More versatile cellar suitable for various occasions",
        ),
    ]


async def _generate_recommendations(
    strengths: str, weaknesses: str, context: dict[str, Any]
) -> list[Recommendation]:
    allowed_aspects = ", ".join(aspect.value for aspect in WineBuyingAspect)
    required_aspects = {
        WineBuyingAspect.COUNTRY.value,
        WineBuyingAspect.REGION.value,
        WineBuyingAspect.GRAPE_VARIETY.value,
        WineBuyingAspect.COLOUR.value,
    }
    style_aspects = {
        WineBuyingAspect.STYLE.value,
        WineBuyingAspect.BODY.value,
        WineBuyingAspect.ACIDITY.value,
        WineBuyingAspect.TANNIN.value,
        WineBuyingAspect.SWEETNESS.value,
        WineBuyingAspect.FOOD_PAIRING.value,
    }

    prompt = f"""Based on the wine cellar analysis, return a structured recommendation plan.

Strengths:
{strengths}

Weaknesses:
{weaknesses}

Generate 2-4 specific, actionable recommendations to improve this wine cellar.

Use the cellar context below to make targets concrete (pick actual values from these lists).

Cellar context:
- Missing colors: {context.get("missing_colors")}
- Low-stock wines: {context.get("low_stock_wines")}
- Top countries: {context.get("top_countries")}
- Low countries: {context.get("low_countries")}
- Top regions: {context.get("top_regions")}
- Low regions: {context.get("low_regions")}
- Top grape varieties: {context.get("top_grapes")}
- Low grape varieties: {context.get("low_grapes")}
- Current colors: {context.get("current_colors")}

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
- Each recommendation must include at least two parameters.
- At least one parameter must use an aspect from {sorted(required_aspects)}.
- At least one parameter must use an aspect from {sorted(style_aspects)} or price_range.
- The target field should be a concise value or range drawn from the cellar context.
- Never use generic targets like "underrepresented countries" or "a colour not dominant".
- The recommendation must always include a price range expressed as a concise human-readable range such as "15-25 EUR".
- quantity_to_buy must be a positive integer.
- Keep the recommendations practical and varied.
"""

    repair_schema = """{
  "recommendations": [
    {
      "title": "string",
      "description": "string",
      "criticality": "low|medium|high|critical",
      "price_range": "string",
      "quantity_to_buy": 1,
      "parameters": [
        {
          "aspect": "country|region|sub_region|price_range|alcohol_level|colour|tannin|acidity|sweetness|body|grape_variety|style|vintage|ageing_potential|food_pairing",
          "target": "string",
          "rationale": "string"
        }
      ],
      "suggested_action": "string",
      "estimated_impact": "string"
    }
  ]
}"""

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

    generic_targets = {
        "underrepresented countries",
        "underrepresented regions",
        "a colour not currently dominant in the cellar",
        "a color not currently dominant in the cellar",
        "missing categories",
        "missing category",
        "underrepresented",
    }

    def _needs_repair(plan: RecommendationPlan) -> str | None:
        for idx, rec in enumerate(plan.recommendations, start=1):
            if len(rec.parameters) < 2:
                return f"Recommendation {idx} must include at least two parameters."
            aspects = {param.aspect.value for param in rec.parameters}
            if not aspects.intersection(required_aspects):
                return f"Recommendation {idx} must include a concrete country/region/grape/colour parameter."
            if not (aspects.intersection(style_aspects) or WineBuyingAspect.PRICE_RANGE.value in aspects):
                return f"Recommendation {idx} must include a style-related or price_range parameter."
            for param in rec.parameters:
                target = param.target.strip().lower()
                if target in generic_targets or "underrepresented" in target:
                    return f"Recommendation {idx} uses a generic target."
        return None

    last_error = ""
    try:
        structured_llm = gemini_flash_3_1_lite.with_structured_output(RecommendationPlan)
        response = await structured_llm.ainvoke(prompt)
        repair_reason = _needs_repair(response)
        if repair_reason:
            raise ValueError(repair_reason)
        return response.recommendations
    except Exception as e:
        last_error = str(e)

    repair_prompt = (
        f"{prompt}\n\nReturn ONLY valid JSON matching this schema. "
        f"No markdown, no comments.\n\nSchema:\n{repair_schema}\n\nPrevious error: {last_error}"
    )

    for _ in range(2):
        try:
            message = HumanMessage(content=repair_prompt)
            response = await gemini_flash_3_1_lite.ainvoke([message])
            raw = response.content if hasattr(response, "content") else str(response)
            json_text = _extract_json(raw)
            if not json_text:
                raise ValueError("No JSON object found in model response")
            data = json.loads(json_text)
            plan = _validate_plan(data)
            repair_reason = _needs_repair(plan)
            if repair_reason:
                raise ValueError(repair_reason)
            return plan.recommendations
        except Exception as e:
            last_error = str(e)
            repair_prompt = repair_prompt.rsplit("Previous error:", 1)[0] + f"Previous error: {last_error}\n"

    return _default_recommendations()


async def run_inventory_audit(user_id: str, query: str) -> WineCellarAnalysis:
    """
    Runs the Inventory Audit agent and returns a WineCellarAnalysis.

    Approach:
    1. Fetch structured cellar data directly from the DB (no text parsing).
    2. Run LLM steps for strengths, weaknesses, and recommendations (same
       pattern as WineCellarAgent).
    3. Compose a WineCellarAnalysis using the shared output models.
    """
    # Step 1: Structured data from DB
    await _publish_inventory_event(
        "action",
        f"Analyzing cellar inventory for user {user_id}.",
    )
    data = await _fetch_cellar_data(user_id)

    await _publish_inventory_event(
        "observation",
        f"Loaded {data['total_wines']} wine entries with {data['total_quantity']} bottles.",
    )

    total_wines = data["total_wines"]
    total_quantity = data["total_quantity"]
    by_color = data["by_color"]
    by_country = data["by_country"]
    by_region = data["by_region"]
    by_grape_variety = data["by_grape_variety"]
    low_stock_wines = data["low_stock_wines"]
    diversity_gaps = data["diversity_gaps"]
    diversity_level = _calculate_diversity_level(data)

    diversity_metrics = {
        "countries": len(by_country),
        "regions": len(by_region),
        "wine_colors": len(by_color),
        "grape_varieties": len(by_grape_variety),
        "total_quantity": total_quantity,
        "distribution_by_country": by_country,
        "distribution_by_color": by_color,
        "distribution_by_grape_variety": by_grape_variety,
    }

    def _ranked_keys(counter: dict[str, int], limit: int = 3, reverse: bool = False) -> list[str]:
        if not counter:
            return []
        return [
            key
            for key in sorted(counter, key=counter.get, reverse=reverse)
            if key
        ][:limit]

    cellar_context = f"""Cellar snapshot:
- Total wine entries: {total_wines}
- Total bottles: {total_quantity}
- By color: {json.dumps(by_color)}
- By country: {json.dumps(by_country)}
- By region: {json.dumps(by_region)}
- By grape variety: {json.dumps(by_grape_variety)}
- Low stock (≤{LOW_STOCK_THRESHOLD} bottles): {low_stock_wines if low_stock_wines else 'none'}
- Missing color categories: {diversity_gaps if diversity_gaps else 'none'}
- Diversity level: {diversity_level}
"""

    # Step 2a: Strengths
    strengths_prompt = f"""{cellar_context}

Identify the top 3-5 strengths of this wine cellar. Consider:
- Well-represented regions or countries
- Good balance of wine colors or grape varieties
- Unique or valuable selections

List each strength as a clear, concise statement."""

    try:
        resp = await gemini_flash_3_1_lite.ainvoke([HumanMessage(content=strengths_prompt)])
        strengths_text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception:
        strengths_text = ""

    await _publish_inventory_event(
        "observation",
        f"Strengths draft: {strengths_text or 'none'}.",
    )

    # Step 2b: Weaknesses
    weaknesses_prompt = f"""{cellar_context}

Identify the top 3-5 weaknesses or areas for improvement in this wine cellar. Consider:
- Underrepresented regions or countries
- Lack of specific wine colors or grape varieties
- Low-stock concerns: {low_stock_wines if low_stock_wines else 'none'}
- Missing categories: {diversity_gaps if diversity_gaps else 'none'}

List each weakness as a clear, concise statement."""

    try:
        resp = await gemini_flash_3_1_lite.ainvoke([HumanMessage(content=weaknesses_prompt)])
        weaknesses_text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception:
        weaknesses_text = ""

    await _publish_inventory_event(
        "observation",
        f"Weaknesses draft: {weaknesses_text or 'none'}.",
    )

    # Step 2c: Recommendations
    recommendation_context = {
        "missing_colors": diversity_gaps,
        "low_stock_wines": low_stock_wines,
        "top_countries": _ranked_keys(by_country, reverse=True),
        "low_countries": _ranked_keys(by_country, reverse=False),
        "top_regions": _ranked_keys(by_region, reverse=True),
        "low_regions": _ranked_keys(by_region, reverse=False),
        "top_grapes": _ranked_keys(by_grape_variety, reverse=True),
        "low_grapes": _ranked_keys(by_grape_variety, reverse=False),
        "current_colors": list(by_color.keys()),
    }
    recommendations = await _generate_recommendations(
        strengths_text,
        weaknesses_text,
        recommendation_context,
    )

    await _publish_inventory_event(
        "observation",
        f"Generated {len(recommendations)} recommendation(s).",
    )

    for idx, rec in enumerate(recommendations, start=1):
        if hasattr(rec, "model_dump"):
            rec_payload = rec.model_dump()
        elif hasattr(rec, "dict"):
            rec_payload = rec.dict()
        else:
            rec_payload = str(rec)
        rec_text = json.dumps(rec_payload, ensure_ascii=True)
        await _publish_inventory_event(
            "observation",
            f"Recommendation {idx}: {rec_text}",
        )

    def _to_str(val: Any) -> str:
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            parts = []
            for el in val:
                parts.append(json.dumps(el) if not isinstance(el, str) else el)
            return "\n".join(parts)
        if isinstance(val, dict):
            return json.dumps(val)
        return str(val)

    strengths_text = _to_str(strengths_text)
    weaknesses_text = _to_str(weaknesses_text)

    # Parse bullet lists into clean string lists
    strengths_list = [
        s.strip() for s in strengths_text.split("\n") if s.strip() and not s.startswith("#")
    ][:5]
    weaknesses_list = [
        w.strip() for w in weaknesses_text.split("\n") if w.strip() and not w.startswith("#")
    ][:5]

    # Compose final output
    overall_assessment = (
        f"This wine cellar contains {total_wines} wine entries representing "
        f"{len(by_country)} countries and {len(by_region)} regions. "
        f"The collection demonstrates a {diversity_level} level of diversity."
    )

    if total_wines > 0:
        avg_per_entry = round(total_quantity / total_wines, 2)
        quantity_observation = (
            f"The user has {total_quantity} total bottles across {total_wines} entries "
            f"(avg {avg_per_entry} per entry)."
        )
    else:
        quantity_observation = "The user has no bottles recorded in the cellar."

    summary = (
        f"{quantity_observation} The cellar shows {len(strengths_list)} key strengths and has "
        f"{len(weaknesses_list)} areas for improvement. "
        f"{len(recommendations)} actionable recommendations have been identified."
    )

    await _publish_inventory_event("final", summary)

    return WineCellarAnalysis(
        total_wines=total_wines,
        quantity_observation=quantity_observation,
        diversity_metrics=diversity_metrics,
        strengths=strengths_list,
        weaknesses=weaknesses_list,
        recommendations=recommendations,
        overall_assessment=overall_assessment,
        summary=summary,
    )
