from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def make_inventory_tools(db: AsyncSession, user_id: str) -> list:
    @tool
    async def get_cellar_summary() -> str:
        """
        Returns a summary of the current wine cellar inventory.
        Includes total bottle count, breakdown by region and color,
        and wines currently at zero or critical stock (1-2 bottles).
        Always call this first to understand the state of the cellar.
        """

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
        )
        rows = result.all()

        if not rows:
            return "The cellar is currently empty."

        total_bottles = sum(row.bottle_count for row in rows)

        by_region: dict[str, int] = {}
        for r in rows:
            by_region[r.region] = by_region.get(r.region, 0) + r.bottle_count
        by_color: dict[str, int] = {}
        for r in rows:
            by_color[r.color] = by_color.get(r.color, 0) + r.bottle_count

        low_stock = [r for r in rows if r.bottle_count <= 2]

        lines = [
            f"Total bottles in stock: {total_bottles}",
            "",
            "Breakdown by region:",
        ]
        for region, count in sorted(by_region.items(), key=lambda x: -x[1]):
            pct = round(count / total_bottles * 100) if total_bottles else 0
            lines.append(f"  {region}: {count} bottles ({pct}%)")

        lines += ["", "Breakdown by color:"]
        for color, count in sorted(by_color.items(), key=lambda x: -x[1]):
            lines.append(f"  {color}: {count} bottles")

        if low_stock:
            lines += ["", "Wines low in stock (2 bottles or fewer):"]
            for r in low_stock:
                lines.append(f"  {r.name} - {r.bottle_count} bottle(s) remaining")

        else:
            lines.append("")
            lines.append("No low stock warnings.")

        return "\n".join(lines)

    @tool
    async def flag_low_stock() -> str:
        """
        Returns wines that are low in stock (2 bottles or fewer).
        Use this when you want to decide if restocking is needed.
        """

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
            .having(func.count(Cellar.id) <= 2)
        )
        rows = result.all()

        if not rows:
            return "No wines are currently low in stock."

        lines = ["Wines with low stock (2 bottles or fewer):"]
        for r in rows:
            lines.append(f"  {r.name} ({r.region}, {r.color}) — {r.bottle_count} bottle(s)")
        return "\n".join(lines)

    return [get_cellar_summary, flag_low_stock]
