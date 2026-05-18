"""Response models for Wine Cellar Analysis Agent"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CriticalityLevel(str, Enum):
    """Criticality levels for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Recommendation(BaseModel):
    """A single recommendation for the wine cellar"""
    title: str = Field(..., description="Short title of the recommendation")
    description: str = Field(..., description="Detailed description of the recommendation")
    criticality: CriticalityLevel = Field(..., description="How critical this recommendation is")
    suggested_action: str = Field(..., description="Specific action to take")
    estimated_impact: str = Field(..., description="Expected impact if implemented")


class WineCellarAnalysis(BaseModel):
    """Structured output from wine cellar analysis"""
    total_wines: int = Field(..., description="Total number of wines in cellar")
    
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
        description="List of recommendations with criticality levels"
    )
    
    overall_assessment: str = Field(
        ..., 
        description="Overall summary assessment of the wine cellar"
    )
    
    summary: str = Field(
        ...,
        description="Brief executive summary for quick understanding"
    )
