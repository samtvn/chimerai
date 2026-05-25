from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.cellar import BottleStatus, Cellar
from apps.api.database.models.wines import Wine
from langchain_core.tools import tool
from sqlalchemy import func, select

LOW_STOCK_THRESHOLD = 3


def make_cellar_overview_tool(user_id: str):
    @tool
    async def get_cellar_overview() -> str:
        """
        Returns a comprehensive overview of the wine cellar.
        Includes:
        - Total bottle count and diversity score
        - Breakdown by color, country, region, and grape variety
        - Wines currently at low stock
        - Missing color categories
        Always call this first to understand the cellar state.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    Wine.name,
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
                .group_by(Wine.id, Wine.name, Wine.country, Wine.region, Wine.color, Wine.grape_variety)
            )
            rows = result.all()

        if not rows:
            return "The cellar is currently empty."

        # Aggregate data
        total_bottles = sum(row.bottle_count for row in rows)
        
        by_color: dict[str, int] = {}
        by_country: dict[str, int] = {}
        by_region: dict[str, int] = {}
        by_variety: dict[str, int] = {}
        low_stock_wines = []
        
        countries_set = set()
        regions_set = set()
        colors_set = set()
        varieties_set = set()

        for row in rows:
            # Aggregations
            by_color[row.color] = by_color.get(row.color, 0) + row.bottle_count
            by_country[row.country] = by_country.get(row.country, 0) + row.bottle_count
            by_region[row.region] = by_region.get(row.region, 0) + row.bottle_count
            by_variety[row.grape_variety] = by_variety.get(row.grape_variety, 0) + row.bottle_count
            
            # Unique dimensions for diversity
            countries_set.add(row.country)
            regions_set.add(row.region)
            colors_set.add(row.color)
            varieties_set.add(row.grape_variety)
            
            # Low stock
            if row.bottle_count <= LOW_STOCK_THRESHOLD:
                low_stock_wines.append((row.name, row.bottle_count))

        # Calculate diversity score
        diversity_score = (
            len(countries_set) * 0.35
            + len(varieties_set) * 0.35
            + len(colors_set) * 0.1
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
            "CELLAR OVERVIEW",
            "===============",
            f"Total bottles: {total_bottles}",
            f"Diversity: {diversity_level} (score: {diversity_score:.1f}/10)",
            "",
        ]

        # By Color
        lines.append("By Color:")
        for color, count in sorted(by_color.items(), key=lambda x: -x[1]):
            pct = round(count / total_bottles * 100) if total_bottles else 0
            lines.append(f"  {color}: {count} bottles ({pct}%)")

        # By Country
        lines.append("")
        lines.append("By Country:")
        for country, count in sorted(by_country.items(), key=lambda x: -x[1]):
            pct = round(count / total_bottles * 100) if total_bottles else 0
            lines.append(f"  {country}: {count} bottles ({pct}%)")

        # By Region
        lines.append("")
        lines.append("By Region:")
        for region, count in sorted(by_region.items(), key=lambda x: -x[1])[:10]:  # Top 10
            pct = round(count / total_bottles * 100) if total_bottles else 0
            lines.append(f"  {region}: {count} bottles ({pct}%)")

        # By Grape Variety
        lines.append("")
        lines.append("By Grape Variety:")
        for variety, count in sorted(by_variety.items(), key=lambda x: -x[1])[:10]:  # Top 10
            pct = round(count / total_bottles * 100) if total_bottles else 0
            lines.append(f"  {variety}: {count} bottles ({pct}%)")

        # Missing color categories
        lines.append("")
        expected_colors = {"red", "white", "rosé", "sparkling", "dessert", "fortified"}
        color_set_lower = {c.lower() if c else "" for c in colors_set}
        missing_colors = expected_colors - color_set_lower
        
        if missing_colors:
            lines.append(f"Missing categories: {', '.join(sorted(missing_colors))}")
        else:
            lines.append("✓ All major color categories represented")

        # Low stock warnings
        lines.append("")
        if low_stock_wines:
            lines.append(f"Low stock (≤{LOW_STOCK_THRESHOLD} bottles):")
            for wine_name, count in sorted(low_stock_wines, key=lambda x: x[1]):
                lines.append(f"  {wine_name}: {count} bottle(s)")
        else:
            lines.append("No low stock warnings.")

        return "\n".join(lines)

    return get_cellar_overview
