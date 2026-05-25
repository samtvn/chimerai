from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select


def make_wines_by_field_tool(user_id: str):
    @tool
    async def get_wines_by_field(field: str, value: str) -> str:
        """
        Get all wines in the cellar filtered by a specific field and value.
        Returns detailed wine information grouped by the filter criteria.

        Args:
            field: One of 'color', 'country', 'region', 'grape_variety'
            value: The value to filter by (e.g. 'red', 'France', 'Bordeaux', 'Chardonnay')
        """
        allowed = {
            "color": Wine.color,
            "country": Wine.country,
            "region": Wine.region,
            "grape_variety": Wine.grape_variety,
        }
        column = allowed.get(field)
        if column is None:
            return f"Error: Invalid field '{field}'. Choose from: {list(allowed.keys())}"

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    Wine.name,
                    Wine.country,
                    Wine.region,
                    Wine.color,
                    Wine.grape_variety,
                    Wine.vintage,
                    func.count(Cellar.id).label("quantity"),
                )
                .join(Cellar, Cellar.wine_id == Wine.id)
                .where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                    column.ilike(f"%{value}%"),
                )
                .group_by(
                    Wine.id,
                    Wine.name,
                    Wine.country,
                    Wine.region,
                    Wine.color,
                    Wine.grape_variety,
                    Wine.vintage,
                )
                .order_by(func.count(Cellar.id).desc())
            )
            rows = result.all()

        if not rows:
            return f"No wines found for {field}='{value}'."

        lines = [f"Wines filtered by {field}='{value}':"]
        lines.append("")
        total_qty = 0
        for row in rows:
            total_qty += row.quantity
            lines.append(
                f"  {row.name} ({row.country}, {row.region}) | "
                f"{row.color} | {row.grape_variety} | {row.vintage or 'NV'} | qty: {row.quantity}"
            )

        lines.append("")
        lines.append(f"Total: {len(rows)} wines, {total_qty} bottles")
        return "\n".join(lines)

    return get_wines_by_field
