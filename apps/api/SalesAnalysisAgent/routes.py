"""FastAPI routes for Sales Analysis Agent."""

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.SalesAnalysisAgent.models import SalesAnalysisFocus, SalesAnalysisResult
from apps.api.SalesAnalysisAgent.service import SalesAnalysisService
from apps.api.database.dependencies import get_read_db
from apps.api.database.repositories.cellar_repository import CellarRepository

router = APIRouter(prefix="/sales", tags=["sales-analysis"])


@router.get("/analysis", response_model=SalesAnalysisResult)
async def get_sales_analysis(
    query: str | None = Query(default=None, description="Free-form analysis focus"),
    wine_name: str | None = Query(default=None, description="Specific wine name"),
    wine_type: str | None = Query(default=None, description="Wine type (e.g., red, white)"),
    price_range: str | None = Query(default=None, description="Price range to filter"),
    lookback_days: int = Query(default=30, ge=7, le=365),
    db=Depends(get_read_db),
):
    """Analyze sales trends against stock levels and return recommendations."""
    try:
        cellar_repo = CellarRepository(db, read_only=True)
        focus = SalesAnalysisFocus(
            query=query,
            wine_name=wine_name,
            wine_type=wine_type,
            price_range=price_range,
        )
        analysis = await SalesAnalysisService.analyze_sales(
            cellar_repo=cellar_repo,
            lookback_days=lookback_days,
            focus=focus,
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sales analysis failed: {str(e)}")
