"""Response models for Wine Cellar Analysis Agent"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class CriticalityLevel(str, Enum):
    """Criticality levels for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WineBuyingAspect(str, Enum):
    """Fixed wine aspects that can be recommended for purchase"""

    COUNTRY = "country"
    REGION = "region"
    SUB_REGION = "sub_region"
    PRICE_RANGE = "price_range"
    ALCOHOL_LEVEL = "alcohol_level"
    COLOUR = "colour"
    TANNIN = "tannin"
    ACIDITY = "acidity"
    SWEETNESS = "sweetness"
    BODY = "body"
    GRAPE_VARIETY = "grape_variety"
    STYLE = "style"
    VINTAGE = "vintage"
    AGEING_POTENTIAL = "ageing_potential"
    FOOD_PAIRING = "food_pairing"


class WineBuyingParameter(BaseModel):
    """A single purchase parameter for a wine recommendation"""

    aspect: WineBuyingAspect = Field(..., description="Fixed aspect used to filter the wine")
    target: str = Field(
        ...,
        description="Desired value or range for the selected aspect",
    )
    rationale: str = Field(
        ...,
        description="Why this aspect is relevant for the recommendation",
    )


class Recommendation(BaseModel):
    """A single recommendation for the wine cellar"""
    title: str = Field(..., description="Short title of the recommendation")
    description: str = Field(..., description="Detailed description of the recommendation")
    criticality: CriticalityLevel = Field(..., description="How critical this recommendation is")
    price_range: str = Field(..., min_length=1, description="Required price range for the search")
    quantity_to_buy: int = Field(..., ge=1, description="How many bottles to buy")
    parameters: List[WineBuyingParameter] = Field(
        ...,
        min_length=1,
        description="Wine purchase parameters expressed with fixed aspects",
    )
    suggested_action: str = Field(..., description="Specific action to take")
    estimated_impact: str = Field(..., description="Expected impact if implemented")


class RecommendationPlan(BaseModel):
    """Structured recommendation output returned by the LLM"""

    recommendations: List[Recommendation] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Validated list of cellar purchase recommendations",
    )


class WineCellarAnalysis(BaseModel):
    """Structured output from wine cellar analysis"""
    total_wines: int = Field(..., description="Total number of wines in cellar")

    quantity_observation: str = Field(
        ...,
        description="Non-agentic observation about bottle quantities"
    )

    diversity_metrics: dict = Field(
        ...,
        description="Metrics about cellar diversity (by country, region, type, colour, etc.)"
    )

    strengths: List[str] = Field(
        ...,
        description="Strengths of the current wine cellar"
    )

    weaknesses: List[str] = Field(
        ...,
        description="Weaknesses or issues identified in the cellar"
    )

    recommendations: List[Recommendation] = Field(
        ...,
        description="List of purchase recommendations with criticality levels and buying parameters",
    )

    overall_assessment: str = Field(
        ...,
        description="Overall summary assessment of the wine cellar"
    )

    summary: str = Field(
        ...,
        description="Brief executive summary for quick understanding"
    )
