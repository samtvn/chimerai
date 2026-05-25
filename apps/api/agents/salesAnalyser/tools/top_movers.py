from datetime import datetime, timedelta, timezone

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.transactions import Transaction, TransactionType
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_top_movers_tool(user_id: str):
    @tool
    async def get_top_movers() -> str:
        """
        Identifies fast movers and slow movers based on sales data and current stock levels.
        Fast movers: wines selling quickly relative to remaining stock
        Slow movers: wines with low sales relative to stock

        Returns sell-through rates to help decide restocking priority.
        Use this to understand which low-stock wines are worth restocking (fast movers)
        vs which should be deprioritized (slow movers).
        """
        async with AsyncSessionLocal() as db:
            # Look back 90 days for sales history
            ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

            # Get sales data per wine (last 90 days)
            sales_result = await db.execute(
                select(
                    Wine.id,
                    Wine.name,
                    Wine.color,
                    Wine.region,
                    Wine.vintage,
                    Wine.producer,
                    func.sum(Transaction.quantity).label("total_sold"),
                )
                .join(Transaction, Transaction.wine_id == Wine.id)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.SALE,
                    Transaction.transaction_date >= ninety_days_ago,
                )
                .group_by(Wine.id, Wine.name, Wine.color, Wine.region, Wine.vintage, Wine.producer)
            )
            sales_rows = {row.id: row for row in sales_result.all()}

            # Get current stock per wine
            stock_result = await db.execute(
                select(
                    Wine.id,
                    Wine.name,
                    func.count(Cellar.id).label("stock_count"),
                )
                .join(Cellar, Cellar.wine_id == Wine.id)
                .where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
                .group_by(Wine.id, Wine.name)
            )
            stock_rows = {row.id: row for row in stock_result.all()}

        # Compute sell-through rates and identify movers
        movers = []
        for wine_id, stock_row in stock_rows.items():
            sales = sales_rows.get(wine_id)
            if not sales:
                continue

            stock = stock_row.stock_count
            sold = sales.total_sold

            if stock + sold > 0:
                sell_through_rate = sold / (stock + sold)
                movers.append(
                    {
                        "wine_id": wine_id,
                        "name": sales.name,
                        "color": sales.color,
                        "region": sales.region,
                        "vintage": sales.vintage,
                        "producer": sales.producer,
                        "sold": sold,
                        "stock": stock,
                        "rate": sell_through_rate,
                    }
                )

        if not movers:
            return "No sales data available to identify movers."

        # Sort by sell-through rate
        movers.sort(key=lambda x: x["rate"], reverse=True)

        fast_movers = movers[:5]
        slow_movers = movers[-5:] if len(movers) > 5 else []

        lines = ["Sales Movers Analysis (last 90 days):", ""]

        if fast_movers:
            lines.append("🔥 Fast Movers (high sell-through, good candidates for restocking):")
            for m in fast_movers:
                rate_pct = round(m["rate"] * 100)
                vintage = m["vintage"] or "NV"
                lines.append(
                    f"  {m['producer']} {m['name']} {vintage} ({m['region']}, {m['color']}) — "
                    f"Sold: {m['sold']}, Stock: {m['stock']}, Sell-through: {rate_pct}%"
                )
        else:
            lines.append("No fast movers identified.")

        lines.append("")

        if slow_movers:
            lines.append("🐌 Slow Movers (low sell-through, reconsider restocking):")
            for m in slow_movers:
                rate_pct = round(m["rate"] * 100)
                vintage = m["vintage"] or "NV"
                lines.append(
                    f"  {m['producer']} {m['name']} {vintage} ({m['region']}, {m['color']}) — "
                    f"Sold: {m['sold']}, Stock: {m['stock']}, Sell-through: {rate_pct}%"
                )
        else:
            lines.append("No slow movers identified.")

        return "\n".join(lines)

    return get_top_movers
