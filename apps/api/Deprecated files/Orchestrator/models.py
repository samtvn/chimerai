"""Structured outputs for the Orchestrator workflow"""

from typing import Optional, List, Literal

from pydantic import BaseModel, Field

from apps.api.WineCellarAgent.models import CriticalityLevel


class MarketSearchCriteria(BaseModel):
    """Only the fields needed to search for wine market availability"""

    colour: Optional[str] = Field(default=None, description="Wine colour to search for")
    price_range: str = Field(..., min_length=1, description="Required price range")
    country: Optional[str] = Field(default=None, description="Target country, if needed")
    region: Optional[str] = Field(default=None, description="Target region, if needed")
    sub_region: Optional[str] = Field(default=None, description="Target sub-region, if needed")
    grape_variety: Optional[str] = Field(
        default=None, description="Target grape variety, if needed"
    )
    style: Optional[str] = Field(default=None, description="Target style, if needed")
    vintage: Optional[str] = Field(default=None, description="Target vintage, if needed")
    alcohol_level: Optional[str] = Field(
        default=None, description="Target alcohol level, if needed"
    )
    tannin: Optional[str] = Field(default=None, description="Target tannin level, if needed")
    acidity: Optional[str] = Field(default=None, description="Target acidity level, if needed")
    sweetness: Optional[str] = Field(default=None, description="Target sweetness level, if needed")
    body: Optional[str] = Field(default=None, description="Target body, if needed")
    ageing_potential: Optional[str] = Field(
        default=None, description="Target ageing potential, if needed"
    )
    food_pairing: Optional[str] = Field(default=None, description="Target food pairing, if needed")


class RecommendationSearchPlan(BaseModel):
    """A single recommendation rewritten as a market-search instruction"""

    title: str = Field(..., description="Recommendation title")
    criticality: CriticalityLevel = Field(..., description="Recommendation criticality")
    priority_rank: int = Field(..., ge=1, description="Rank in execution order")
    should_call_market_analysis: bool = Field(
        ..., description="Whether to call market analysis for this item"
    )
    quantity_to_buy: int = Field(..., ge=1, description="How many bottles to search for")
    criteria: MarketSearchCriteria = Field(..., description="Minimal structured search constraints")


class OrchestratorSearchPlan(BaseModel):
    """Final structured output emitted by the orchestrator"""

    recommendations: List[RecommendationSearchPlan] = Field(
        ...,
        min_length=1,
        description="Priority ordered recommendations ready for market search",
    )

class OrchestratorDecision(BaseModel):

    next_action: Literal[
        "build_search_plan",
        "sales_analysis",
        "run_market_analysis",
        "end",
    ]

    reasoning: str
