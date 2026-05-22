from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from database.models.recommendations import Recommendation
from .base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    def __init__(self, session: AsyncSession, read_only: bool = False):
        super().__init__(session, read_only)

    async def get_user_recommendations(self, user_id: UUID, limit: int = 50) -> List[Recommendation]:
        result = await self.session.execute(
            select(Recommendation)
            .options(selectinload(Recommendation.wine))
            .where(Recommendation.user_id == user_id)
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_unread_count(self, user_id: UUID) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Recommendation.id)).where(
                and_(Recommendation.user_id == user_id, Recommendation.read.is_(False))
            )
        )
        return result.scalar() or 0
