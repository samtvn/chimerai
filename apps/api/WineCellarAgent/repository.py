"""Database service for Wine Cellar Agent to fetch cellar data"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class WineCellarRepository:
    """Repository for accessing wine cellar data"""

    _IN_CELLAR_STATUS = "in_cellar"

    def __init__(self, db: AsyncSession):
        """Initialize with an already-open AsyncSession"""
        if db is None:
            raise ValueError("db session is required")
        self.db = db
        self._user_id: Optional[UUID] = None

    async def _get_only_user_id(self) -> Optional[UUID]:
        """Fetch and cache the only user id in the database."""
        if self._user_id is not None:
            return self._user_id

        result = await self.db.execute(text("SELECT id FROM users LIMIT 1"))
        self._user_id = result.scalar()
        return self._user_id

    async def get_all_wines(self) -> List[dict]:
        """Fetch all wines from the user's cellar as dict rows"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return []

        result = await self.db.execute(
            text(
                "SELECT c.user_id, c.wine_id AS cellar_wine_id, c.transaction_id, c.status, "
                "w.id AS wine_id, w.name, w.producer, w.country, w.region, w.appellation, "
                "w.vintage, w.grape_variety, w.color, w.alcohol, w.drink_from, w.drink_to, w.market_price "
                "FROM \"Cellar\" c "
                "JOIN wines w ON c.wine_id = w.id "
                "WHERE c.user_id = :user_id AND c.status = :status"
            ),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return [dict(r._mapping) for r in result.all()]

    async def get_wine_count(self) -> int:
        """Get total count of bottles in the user's cellar"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return 0
        result = await self.db.execute(
            text("SELECT count(*) FROM \"Cellar\" WHERE user_id = :user_id AND status = :status"),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return int(result.scalar() or 0)

    async def get_total_quantity(self) -> int:
        """Get total quantity of bottles for the user"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return 0
        result = await self.db.execute(
            text("SELECT count(*) FROM \"Cellar\" WHERE user_id = :user_id AND status = :status"),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return int(result.scalar() or 0)

    async def get_wines_by_country(self) -> dict[str, int]:
        """Get breakdown of wines by country"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self.db.execute(
            text(
                "SELECT w.country, count(*) AS count "
                "FROM \"Cellar\" c "
                "JOIN wines w ON c.wine_id = w.id "
                "WHERE c.user_id = :user_id AND c.status = :status "
                "GROUP BY w.country"
            ),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_region(self) -> dict[str, int]:
        """Get breakdown of wines by region"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self.db.execute(
            text(
                "SELECT w.region, count(*) AS count "
                "FROM \"Cellar\" c "
                "JOIN wines w ON c.wine_id = w.id "
                "WHERE c.user_id = :user_id AND c.status = :status "
                "GROUP BY w.region"
            ),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_color(self) -> dict[str, int]:
        """Get breakdown of wines by color"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self.db.execute(
            text(
                "SELECT w.color AS color, count(*) AS count "
                "FROM \"Cellar\" c "
                "JOIN wines w ON c.wine_id = w.id "
                "WHERE c.user_id = :user_id AND c.status = :status "
                "GROUP BY w.color"
            ),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_grape_variety(self) -> dict[str, int]:
        """Get breakdown of wines by grape variety"""
        user_id = await self._get_only_user_id()
        if not user_id:
            return {}
        result = await self.db.execute(
            text(
                "SELECT w.grape_variety AS grape_variety, count(*) AS count "
                "FROM \"Cellar\" c "
                "JOIN wines w ON c.wine_id = w.id "
                "WHERE c.user_id = :user_id AND c.status = :status "
                "GROUP BY w.grape_variety"
            ),
            {"user_id": user_id, "status": self._IN_CELLAR_STATUS},
        )
        return {row[0]: row[1] for row in result.all()}
