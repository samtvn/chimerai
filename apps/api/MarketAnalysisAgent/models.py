"""Structured models for market analysis outputs"""
from typing import Optional, List

from pydantic import BaseModel, Field


class MarketAnalysisCriteria(BaseModel):
    """Filters used to select a wine from the market"""

    colour: Optional[str] = Field(default=None, description="Wine colour to search for")
    price_range: str = Field(..., min_length=1, description="Required price range")
    country: Optional[str] = Field(default=None, description="Target country, if needed")
    region: Optional[str] = Field(default=None, description="Target region, if needed")
    sub_region: Optional[str] = Field(default=None, description="Target sub-region, if needed")
    grape_variety: Optional[str] = Field(default=None, description="Target grape variety, if needed")
    style: Optional[str] = Field(default=None, description="Target style, if needed")
    vintage: Optional[str] = Field(default=None, description="Target vintage, if needed")
    alcohol_level: Optional[str] = Field(default=None, description="Target alcohol level, if needed")
    tannin: Optional[str] = Field(default=None, description="Target tannin level, if needed")
    acidity: Optional[str] = Field(default=None, description="Target acidity level, if needed")
    sweetness: Optional[str] = Field(default=None, description="Target sweetness level, if needed")
    body: Optional[str] = Field(default=None, description="Target body, if needed")
    ageing_potential: Optional[str] = Field(default=None, description="Target ageing potential, if needed")
    food_pairing: Optional[str] = Field(default=None, description="Target food pairing, if needed")


class MarketAnalysisResult(BaseModel):
    """Structured output for a market analysis recommendation"""

    recommendation_title: str = Field(..., description="Title of the recommendation")
    wine_id: int = Field(..., description="Selected wine ID")
    wine_name: str = Field(..., description="Selected wine name")
    producer: str = Field(..., description="Selected wine producer")
    country: Optional[str] = Field(default=None, description="Selected wine country")
    region: Optional[str] = Field(default=None, description="Selected wine region")
    sub_region: Optional[str] = Field(default=None, description="Selected wine sub-region")
    vintage: Optional[str] = Field(default=None, description="Selected wine vintage")
    grape_variety: Optional[str] = Field(default=None, description="Selected wine grape variety")
    colour: Optional[str] = Field(default=None, description="Selected wine colour")
    price_per_bottle: Optional[float] = Field(default=None, description="Market price per bottle")
    quantity: int = Field(..., ge=1, description="Quantity to buy")
    total_price: Optional[float] = Field(default=None, description="Total price for the quantity")
    fit_score: float = Field(..., ge=0.0, le=1.0, description="How well the wine fits the criteria")
    fit_notes: List[str] = Field(default_factory=list, description="Notes describing the fit")
    criteria: MarketAnalysisCriteria = Field(..., description="Criteria used for the selection")
