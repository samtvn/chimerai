"""Structured models for sales analysis outputs."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CriticalityLevel(str, Enum):
    """Criticality levels for recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationType(str, Enum):
    """Types of sales recommendations."""

    INCREASE_STOCK = "increase_stock"
    REDUCE_STOCK = "reduce_stock"
    ADJUST_PRICE = "adjust_price"
    MONITOR = "monitor"


class SalesAnalysisFocus(BaseModel):
    """Optional focus for sales analysis."""

    query: Optional[str] = Field(default=None, description="Free-form focus query")
    wine_name: Optional[str] = Field(default=None, description="Specific wine name")
    wine_type: Optional[str] = Field(default=None, description="Wine type (e.g., red, white)")
    price_range: Optional[str] = Field(default=None, description="Price range filter")
    wine_id: Optional[int] = Field(default=None, description="Resolved wine ID")


class SalesAnalysisQuery(BaseModel):
    """Parsed intent for the sales analysis focus."""

    wine_name: Optional[str] = Field(default=None, description="Specific wine name")
    wine_type: Optional[str] = Field(default=None, description="Wine type (e.g., red, white)")
    price_range: Optional[str] = Field(default=None, description="Price range filter")


class SalesMover(BaseModel):
    """Wine sales and stock snapshot for movers."""

    wine_id: int = Field(..., description="Wine ID")
    wine_name: str = Field(..., description="Wine name")
    stock_quantity: int = Field(..., ge=0, description="Current stock quantity")
    sales_recent: int = Field(..., ge=0, description="Recent sales quantity")
    sell_through_rate: float = Field(..., ge=0.0, le=1.0, description="Sell-through rate")


class SalesRecommendation(BaseModel):
    """A single recommendation based on sales analysis."""

    title: str = Field(..., description="Short title of the recommendation")
    description: str = Field(..., description="Detailed description of the recommendation")
    criticality: CriticalityLevel = Field(..., description="How critical the recommendation is")
    recommendation_type: RecommendationType = Field(..., description="Type of recommendation")
    target: str = Field(..., description="Target wine or segment for this recommendation")
    suggested_action: str = Field(..., description="Recommended action (non-binding)")
    evidence: str = Field(..., description="Metrics or observations supporting the recommendation")
    expected_impact: str = Field(..., description="Expected impact if implemented")


class SalesRecommendationPlan(BaseModel):
    """Structured recommendation output returned by the LLM."""

    recommendations: List[SalesRecommendation] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Validated list of sales recommendations",
    )


class SalesAnalysisResult(BaseModel):
    """Structured output for sales analysis."""

    focus: dict = Field(..., description="Focus used for the analysis")
    stock_metrics: dict = Field(..., description="Current stock metrics")
    sales_metrics: dict = Field(..., description="Sales metrics and trends")
    movers: dict = Field(..., description="Fast and slow movers")
    trend_observations: List[str] = Field(..., description="Key trend observations")
    recommendations: List[SalesRecommendation] = Field(
        ...,
        description="List of sales recommendations",
    )
    overall_assessment: str = Field(..., description="Overall assessment of sales vs stock")
    summary: str = Field(..., description="Executive summary for quick understanding")
