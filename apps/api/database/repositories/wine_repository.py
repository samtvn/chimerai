from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from database.models.wines import Wine
from .base import BaseRepository


class WineRepository(BaseRepository[Wine]):
    model = Wine
    
    def __init__(self, session: AsyncSession, read_only: bool = False):
        """Initialize WineRepository.
        
        Args:
            session: AsyncSession instance
            read_only: If True, only read operations are allowed
        """
        super().__init__(session, read_only)
    
    async def get_by_color(self, color: str, limit: int = 100) -> List[Wine]:
        """Get wines by color"""
        result = await self.session.execute(
            select(Wine).where(Wine.color == color).limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_region(self, region: str, limit: int = 100) -> List[Wine]:
        """Get wines by region"""
        result = await self.session.execute(
            select(Wine).where(Wine.region == region).limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_producer(self, producer: str, limit: int = 100) -> List[Wine]:
        """Get wines by producer"""
        result = await self.session.execute(
            select(Wine).where(Wine.producer == producer).limit(limit)
        )
        return result.scalars().all()
