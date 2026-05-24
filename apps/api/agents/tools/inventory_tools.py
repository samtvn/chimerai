from langchain_core.tools import tool
from sqlalchemy import func, select

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine


def make_inventory_tools(user_id: str) -> list:
    @tool
    async def get_cellar_summary() -> str:
        """
        Returns a summary of the current wine cellar inventory.
        Includes total bottle count, breakdown by region and color,
        and wines currently at zero or critical stock (1-2 bottles).
        Always call this first to understand the state of the cellar.
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
                .having(func.count(Cellar.id) <= 2)
            )
            rows = result.all()

        if not rows:
            return "No wines are currently low in stock."

        lines = ["Wines with low stock (2 bottles or fewer):"]
        for r in rows:
            lines.append(f"  {r.name} ({r.region}, {r.color}) — {r.bottle_count} bottle(s)")
        return "\n".join(lines)

    @tool
    async def get_cellar_analysis() -> str:
        """
        Returns a deep diversity and balance analysis of the wine cellar.
        Includes diversity score (excellent/good/moderate/limited), counts by country/region/color/grape variety,
        and identifies any dimensions with zero representation (gaps).
        Use this to understand cellar balance and identify weak spots.
        """
        async with AsyncSessionLocal() as db:
            # Get all wines in cellar
            result = await db.execute(
                select(
                    Wine.country,
                    Wine.region,
                    Wine.color,
                    Wine.grape_variety,
                    func.count(Cellar.id).label("bottle_count"),
                )
                .join(Cellar, Cellar.wine_id == Wine.id)
                .where(
                    Cellar.user_id == user_id,
                    Cellar.status == BottleStatus.IN_CELLAR,
                )
                .group_by(Wine.id, Wine.country, Wine.region, Wine.color, Wine.grape_variety)
            )
            rows = result.all()

        if not rows:
            return "The cellar is empty. No diversity to analyze."

        # Extract unique dimensions
        countries = set()
        regions = set()
        colors = set()
        varieties = set()
        total_bottles = 0

        for row in rows:
            if row.country:
                countries.add(row.country)
            if row.region:
                regions.add(row.region)
            if row.color:
                colors.add(row.color)
            if row.grape_variety:
                varieties.add(row.grape_variety)
            total_bottles += row.bottle_count

        # Calculate diversity score (weighted formula)
        diversity_score = (
            len(countries) * 0.35
            + len(varieties) * 0.35
            + len(colors) * 0.1
            + min(total_bottles / 50, 10) * 0.2
        )

        if diversity_score >= 7:
            diversity_level = "excellent"
        elif diversity_score >= 5:
            diversity_level = "good"
        elif diversity_score >= 3:
            diversity_level = "moderate"
        else:
            diversity_level = "limited"

        # Build output
        lines = [
            "Cellar Diversity Analysis",
            "========================",
            f"Total bottles: {total_bottles}",
            f"Diversity level: {diversity_level} (score: {diversity_score:.1f}/10)",
            "",
            f"Unique countries: {len(countries)}",
            f"Unique regions: {len(regions)}",
            f"Unique colors: {len(colors)}",
            f"Unique grape varieties: {len(varieties)}",
            "",
        ]

        # Expected categories (basic wine colors)
        expected_colors = {"red", "white", "rosé", "sparkling", "dessert", "fortified"}
        color_set_lower = {c.lower() if c else "" for c in colors}
        missing_colors = expected_colors - color_set_lower

        if missing_colors:
            lines.append(f"Missing color categories: {', '.join(sorted(missing_colors))}")
        else:
            lines.append("✓ All major color categories represented")

        return "\n".join(lines)

    return [get_cellar_summary, flag_low_stock, get_cellar_analysis]
