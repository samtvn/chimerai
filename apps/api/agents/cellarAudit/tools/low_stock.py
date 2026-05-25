from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select

LOW_STOCK_THRESHOLD = 3


def make_flag_low_stock_tool(user_id: str):
    @tool
    async def flag_low_stock() -> str:
        """
        Returns wines that are low in stock (2 bottles or fewer).
        Use this when you want to decide if restocking is needed.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    Wine.name,
                    Wine.region,
                    Wine.color,
                    func.count(Cellar.id).label("bottle_count"),
                )
                .join(Cellar, Cellar.wine_id == Wine.id)
                .where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
                .group_by(Wine.id, Wine.name, Wine.region, Wine.color)
                .having(func.count(Cellar.id) <= LOW_STOCK_THRESHOLD)
            )
            rows = result.all()

        if not rows:
            return "No wines are currently low in stock."

        lines = [f"Wines with low stock ({LOW_STOCK_THRESHOLD} bottles or fewer):"]
        for r in rows:
            lines.append(f"  {r.name} ({r.region}, {r.color}) — {r.bottle_count} bottle(s)")
        return "\n".join(lines)

    return flag_low_stock
