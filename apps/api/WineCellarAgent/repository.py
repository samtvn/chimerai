"""Database service for Wine Cellar Agent to fetch wine data"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class WineCellarRepository:
    """Repository for accessing wine cellar data"""

    _USER_ID = 9

    def __init__(self, db: AsyncSession):
        """Initialize with an already-open AsyncSession"""
        if db is None:
            raise ValueError("db session is required")
        self.db = db

    async def _column_exists(self, session: AsyncSession, column_name: str) -> bool:
        """Check whether a column exists on the `bottles` table."""
        from sqlalchemy import text
        q = text("SELECT 1 FROM information_schema.columns WHERE table_name='bottles' AND column_name = :col LIMIT 1")
        result = await session.execute(q, {"col": column_name})
        return result.scalar() is not None

    async def get_all_wines(self) -> List[dict]:
        """Fetch all wines from the cellar as dict rows (robust to schema differences)"""
        result = await self.db.execute(
            text(
                "SELECT b.*, w.display_name, w.country, w.region, w.colour, w.\"type\", w.sub_type "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id"
            ),
            {"user_id": self._USER_ID},
        )
        return [dict(r._mapping) for r in result.all()]

    async def get_wine_count(self) -> int:
        """Get total count of wines in cellar"""
        result = await self.db.execute(
            text("SELECT count(*) FROM bottles WHERE user_id = :user_id"),
            {"user_id": self._USER_ID},
        )
        return int(result.scalar() or 0)

    async def get_total_quantity(self) -> int:
        """Get total quantity of bottles for the user"""
        result = await self.db.execute(
            text("SELECT COALESCE(SUM(quantity), 0) FROM bottles WHERE user_id = :user_id"),
            {"user_id": self._USER_ID},
        )
        return int(result.scalar() or 0)

    async def get_wines_by_country(self) -> dict[str, int]:
        """Get breakdown of wines by country"""
        result = await self.db.execute(
            text(
                "SELECT w.country, count(*) AS count "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id "
                "GROUP BY w.country"
            ),
            {"user_id": self._USER_ID},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_region(self) -> dict[str, int]:
        """Get breakdown of wines by region"""
        result = await self.db.execute(
            text(
                "SELECT w.region, count(*) AS count "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id "
                "GROUP BY w.region"
            ),
            {"user_id": self._USER_ID},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_type(self) -> dict[str, int]:
        """Get breakdown of wines by type"""
        result = await self.db.execute(
            text(
                "SELECT w.\"type\" AS type, count(*) AS count "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id "
                "GROUP BY w.\"type\""
            ),
            {"user_id": self._USER_ID},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_colour(self) -> dict[str, int]:
        """Get breakdown of wines by colour"""
        result = await self.db.execute(
            text(
                "SELECT w.colour AS colour, count(*) AS count "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id "
                "GROUP BY w.colour"
            ),
            {"user_id": self._USER_ID},
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_sub_type(self) -> dict[str, int]:
        """Get breakdown of wines by sub_type"""
        result = await self.db.execute(
            text(
                "SELECT w.sub_type AS sub_type, count(*) AS count "
                "FROM bottles b "
                "JOIN wines w ON b.wine_id = w.lwin "
                "WHERE b.user_id = :user_id "
                "GROUP BY w.sub_type"
            ),
            {"user_id": self._USER_ID},
        )
        return {row[0]: row[1] for row in result.all()}
