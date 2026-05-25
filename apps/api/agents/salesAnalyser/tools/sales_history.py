from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models import Transaction, TransactionType, Wine
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_sales_history_tool(user_id: str):
    @tool
    async def get_sales_history(wine_name: str) -> str:
        """
        Takes a wine name (or partial name) as input. Provide the wine_name parameter to filter by a specific wine.
        Returns a summary of the user's sales history.
        Includes total bottles sold, wine name, region, and color.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    Wine.name,
                    Wine.region,
                    Wine.color,
                    Wine.vintage,
                    Wine.producer,
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
            lines.append(
                f"  {r.name} ({r.region}, {r.color}, {r.vintage}, {r.producer}) — {r.total_sold} bottle(s) sold"
            )
        return "\n".join(lines)

    return get_sales_history
