from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.dependencies import get_read_db, get_demo_user_id
from database.repositories.recommendations_repository import RecommendationRepository

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/recommendations")
async def list_recommendations(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_read_db),
):
    user_id = await get_demo_user_id(db)
    repo = RecommendationRepository(db, read_only=True)
    recommendations = await repo.get_user_recommendations(user_id, limit)
    return {
        "recommendations": [
            {
                "id": str(a.id),
                "wine_id": a.wine_id,
                "wine_name": a.wine.name if a.wine else None,
                "wine_producer": a.wine.producer if a.wine else None,
                "quantity": a.quantity,
                "market_price": a.market_price,
                "priority_score": a.priority_score,
                "recommendation_reason": a.recommendation_reason,
                "created_at": a.created_at.isoformat(),
            }
            for a in recommendations
        ]
    }
