from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_wine_count_tool(user_id: str):
    @tool
    async def get_wine_count() -> int:
        """Get total count of bottles in the user's cellar"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count(Cellar.id)).where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
            )
        return int(result.scalar() or 0)

    return get_wine_count
