"""Database service for Wine Cellar Agent to fetch wine data"""
import os
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()


def get_url(env_var: str):
    """Convert PostgreSQL URL to async compatible format"""
    url = os.environ.get(env_var)
    if url and url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class WineCellarRepository:
    """Repository for accessing wine cellar data"""
    
    def __init__(self, db_url: str | None = None):
        """Initialize with optional custom database URL (defaults to DATABASE_RO_URL)"""
        self.db_url = db_url or get_url("DATABASE_RO_URL")
        if not self.db_url:
            raise ValueError("DATABASE_RO_URL environment variable not set")
        
        self.engine = create_async_engine(self.db_url, pool_pre_ping=True)
        self.AsyncSessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def _column_exists(self, session: AsyncSession, column_name: str) -> bool:
        """Check whether a column exists on the `wines` table."""
        from sqlalchemy import text
        q = text("SELECT 1 FROM information_schema.columns WHERE table_name='wines' AND column_name = :col LIMIT 1")
        result = await session.execute(q, {"col": column_name})
        return result.scalar() is not None

    async def get_all_wines(self) -> List[dict]:
        """Fetch all wines from the cellar as dict rows (robust to schema differences)"""
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT * FROM wines"))
            return [dict(r._mapping) for r in result.all()]

    async def get_wine_count(self) -> int:
        """Get total count of wines in cellar"""
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT count(*) FROM wines"))
            return int(result.scalar() or 0)

    async def get_wines_by_country(self) -> dict[str, int]:
        """Get breakdown of wines by country"""
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT country, count(*) AS count FROM wines GROUP BY country"))
            return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_region(self) -> dict[str, int]:
        """Get breakdown of wines by region"""
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT region, count(*) AS count FROM wines GROUP BY region"))
            return {row[0]: row[1] for row in result.all()}

    async def get_wines_by_type(self) -> dict[str, int]:
        """Get breakdown of wines by a reasonable 'type' column (tries several fallbacks)"""
        async with self.AsyncSessionLocal() as session:
            for col in ("body_style", "wine_color", "grape_variety"):
                q = text(f"SELECT {col} AS type, count(*) AS count FROM wines GROUP BY {col}")
                try:
                    result = await session.execute(q)
                    if result:
                        rows = result.all()
                        if rows:
                            return {row[0]: row[1] for row in rows}
                except Exception:
                    continue
            return {}

    async def get_wines_by_colour(self) -> dict[str, int]:
        """Get breakdown of wines by colour (fallbacks)"""
        async with self.AsyncSessionLocal() as session:
            for col in ("wine_color", "wine_color", "body_style"):
                q = text(f"SELECT {col} AS colour, count(*) AS count FROM wines GROUP BY {col}")
                try:
                    result = await session.execute(q)
                    rows = result.all()
                    if rows:
                        return {row[0]: row[1] for row in rows}
                except Exception:
                    continue
            return {}

    async def get_wines_by_sub_type(self) -> dict[str, int]:
        """Get breakdown of wines by sub_type (tries grape_variety, body_style)"""
        async with self.AsyncSessionLocal() as session:
            for col in ("grape_variety", "body_style"):
                q = text(f"SELECT {col} AS sub_type, count(*) AS count FROM wines GROUP BY {col}")
                try:
                    result = await session.execute(q)
                    rows = result.all()
                    if rows:
                        return {row[0]: row[1] for row in rows}
                except Exception:
                    continue
            return {}
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
