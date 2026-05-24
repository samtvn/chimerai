from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.transactions import Transaction, TransactionType
from apps.api.database.models.wines import Wine
from apps.api.database.models.cellar import Cellar, BottleStatus
from langchain_core.tools import tool
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone


def make_sales_tools(user_id: str) -> list:
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
        async with AsyncSessionLocal() as db:
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

    @tool
    async def get_sales_movers() -> str:
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
                    func.sum(Transaction.quantity).label("total_sold"),
                )
                .join(Transaction, Transaction.wine_id == Wine.id)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.SALE,
                    Transaction.created_at >= ninety_days_ago,
                )
                .group_by(Wine.id, Wine.name, Wine.color, Wine.region)
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
                lines.append(
                    f"  {m['name']} ({m['region']}, {m['color']}) — "
                    f"Sold: {m['sold']}, Stock: {m['stock']}, Sell-through: {rate_pct}%"
                )
        else:
            lines.append("No fast movers identified.")

        lines.append("")

        if slow_movers:
            lines.append("🐌 Slow Movers (low sell-through, reconsider restocking):")
            for m in slow_movers:
                rate_pct = round(m["rate"] * 100)
                lines.append(
                    f"  {m['name']} ({m['region']}, {m['color']}) — "
                    f"Sold: {m['sold']}, Stock: {m['stock']}, Sell-through: {rate_pct}%"
                )
        else:
            lines.append("No slow movers identified.")

        return "\n".join(lines)

    return [get_sales_history, get_top_wines, get_sales_movers]

