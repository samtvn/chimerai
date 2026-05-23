from apps.api.database.models.transactions import Transaction, TransactionType
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def make_sales_tools(db: AsyncSession, user_id: str) -> list:
    @tool
    async def get_sales_history(wine_name: str) -> str:
        """
        Takes a wine name (or partial name) as input. Provide the wine_name parameter to filter by a specific wine.
        Returns a summary of the user's sales history.
        Includes total bottles sold, wine name, region, and color.
        """

        result = await db.execute(
            select(
                Wine.name,
                Wine.region,
                Wine.color,
                func.sum(Transaction.quantity).label("total_sold"),
            )
            .join(Transaction, Transaction.wine_id == Wine.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
                Wine.name.ilike(f"%{wine_name}%"),
            )
            .group_by(Wine.id, Wine.name, Wine.region, Wine.color)
            .order_by(func.sum(Transaction.quantity).desc())
        )

        rows = result.all()

        if not rows:
            return "No wines have been sold."

        lines = ["Sales history:"]
        for r in rows:
            lines.append(f"  {r.name} ({r.region}, {r.color}) — {r.total_sold} bottle(s) sold")
        return "\n".join(lines)

    @tool
    async def get_top_wines() -> str:
        """
        Returns wines that are the most sold.
        Use this when you want to understand the top-selling wines, which can inform restocking decisions and identify popular choices among customers.
        This holds name, region, color, and total bottles sold for each wine. Always call this after getting the cellar summary to see which wines are performing best in sales.
        """

        result = await db.execute(
            select(
                Wine.name,
                Wine.region,
                Wine.color,
                func.sum(Transaction.quantity).label("total_sold"),
            )
            .join(Transaction, Transaction.wine_id == Wine.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
            )
            .group_by(Wine.id, Wine.name, Wine.region, Wine.color)
            .order_by(func.sum(Transaction.quantity).desc())
            .limit(20)
        )
        rows = result.all()

        if not rows:
            return "No wines have been sold."

        lines = ["Top-selling wines:"]
        for r in rows:
            lines.append(f"  {r.name} ({r.region}, {r.color}) — {r.total_sold} bottle(s) sold")
        return "\n".join(lines)

    return [get_sales_history, get_top_wines]
