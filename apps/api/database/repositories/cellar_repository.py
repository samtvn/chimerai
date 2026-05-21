from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from ..models.cellar import Cellar, BottleStatus
from .base import BaseRepository


class CellarRepository(BaseRepository[Cellar]):
    model = Cellar

    def __init__(self, session: AsyncSession, read_only: bool = False):
        """Initialize CellarRepository.

        Args:
            session: AsyncSession instance
            read_only: If True, only read operations are allowed
        """
        super().__init__(session, read_only)

    async def get_user_cellar(self, user_id: UUID, limit: int = 100) -> List[Cellar]:
        """Get all bottles in a user's cellar"""
        result = await self.session.execute(
            select(Cellar).where(Cellar.user_id == user_id).limit(limit)
        )
        return result.scalars().all()

    async def get_user_cellar_in_stock(self, user_id: UUID, limit: int = 100) -> List[Cellar]:
        """Get all in-stock bottles in a user's cellar"""
        result = await self.session.execute(
            select(Cellar)
            .where(
                and_(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_sold_bottles(self, user_id: UUID, limit: int = 100) -> List[Cellar]:
        """Get all sold bottles from a user's cellar"""
        result = await self.session.execute(
            select(Cellar)
            .where(
                and_(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.SOLD
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def get_wine_in_cellar(self, user_id: UUID, wine_id: int, limit: int = 100) -> List[Cellar]:
        """Get all bottles of a specific wine in a user's cellar"""
        result = await self.session.execute(
            select(Cellar)
            .where(
                and_(
                    Cellar.user_id == user_id,
                    Cellar.wine_id == wine_id
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_transaction(self, transaction_id: UUID) -> List[Cellar]:
        """Get all cellar entries linked to a transaction"""
        result = await self.session.execute(
            select(Cellar).where(Cellar.transaction_id == transaction_id)
        )
        return result.scalars().all()
