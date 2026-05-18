"""Example FastAPI routes for Wine Cellar Analysis Agent"""
from fastapi import APIRouter, HTTPException
from api.WineCellarAgent.service import WineCellarAnalysisService
from api.WineCellarAgent.models import WineCellarAnalysis

router = APIRouter(prefix="/cellar", tags=["wine-cellar"])


@router.get("/analysis", response_model=WineCellarAnalysis)
async def get_cellar_analysis():
    """
    Analyze the wine cellar for diversity and get recommendations
    
    Returns:
        WineCellarAnalysis: Complete analysis with recommendations and criticality levels
    
    Raises:
        HTTPException: If analysis fails (500 error)
    """
    try:
        analysis = await WineCellarAnalysisService.analyze_cellar()
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wine cellar analysis failed: {str(e)}")


@router.get("/analysis/summary")
async def get_cellar_summary():
    """
    Get a summary of the wine cellar analysis (quick version)
    
    Returns:
        dict: Simplified summary with key metrics and top recommendations
    """
    try:
        analysis = await WineCellarAnalysisService.analyze_cellar()
        return {
            "total_wines": analysis.total_wines,
            "diversity_level": _calculate_diversity_level(analysis.diversity_metrics),
            "key_strengths": analysis.strengths[:3],
            "priority_improvements": [
                {
                    "title": rec.title,
                    "criticality": rec.criticality,
                    "action": rec.suggested_action
                }
                for rec in analysis.recommendations
                if rec.criticality in ["high", "critical"]
            ][:3],
            "summary": analysis.summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


def _calculate_diversity_level(metrics: dict) -> str:
    """Helper to calculate diversity level from metrics"""
    score = (
        metrics.get('countries', 0) * 0.4 +
        metrics.get('wine_types', 0) * 0.3 +
        min(len(metrics.get('distribution_by_country', {})) / 50, 10) * 0.3
    )
    
    if score >= 8:
        return "Excellent"
    elif score >= 6:
        return "Good"
    elif score >= 4:
        return "Moderate"
    else:
        return "Limited"


# Integration in main.py:
# from WineCellarAgent.routes import router as cellar_router
# app.include_router(cellar_router)
