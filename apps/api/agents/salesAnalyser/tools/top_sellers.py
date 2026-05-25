from typing import Optional

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models import Transaction, TransactionType, Wine
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_top_sellers_tool(user_id: str):
    @tool
    async def get_top_sellers(
        field: Optional[str] = None, value: Optional[str] = None, limit: int = 20
    ) -> str:
        """
        Get top N selling wines, optionally filtered by a field/value pair.

        Args:
            field: Optional. One of 'color', 'country', 'region', 'grape_variety'
            value: Optional. The value to filter by (e.g. 'red', 'France', 'Bordeaux', 'Chardonnay'). Required if field is provided.
            limit: The maximum number of top sellers to return (default is 20)
        """
        allowed = {
            "color": Wine.color,
            "country": Wine.country,
            "region": Wine.region,
            "grape_variety": Wine.grape_variety,
        }

        filters = [
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.SALE,
        ]

        if field is not None:
            column = allowed.get(field)
            if column is None:
                return f"Error: Invalid field '{field}'. Choose from: {list(allowed.keys())}"
            if value is None:
                return "Error: 'value' is required when 'field' is provided."
            filters.append(column.ilike(f"%{value}%"))

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    Wine.name,
                    Wine.producer,
                    Wine.vintage,
                    Wine.region,
                    Wine.color,
                    func.sum(Transaction.quantity).label("total_sold"),
                )
                .join(Transaction, Transaction.wine_id == Wine.id)
                .where(*filters)
                .group_by(Wine.id, Wine.name, Wine.producer, Wine.vintage, Wine.region, Wine.color)
                .order_by(func.sum(Transaction.quantity).desc())
                .limit(limit)
            )
            rows = result.all()

        if not rows:
            return "No wines have been sold."

        label = f" ({field}={value})" if field else ""
        lines = [f"Top-selling wines{label}:"]
        for r in rows:
            vintage = r.vintage or "NV"
            lines.append(f"  {r.producer} {r.name} {vintage} ({r.region}, {r.color}) — {r.total_sold} bottle(s) sold")
        return "\n".join(lines)

    return get_top_sellers
