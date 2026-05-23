"""Service layer for wine-card pricing, menu export, and analysis."""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from .models import (
    InventoryItem,
    MenuAnalysisResult,
    MenuExportResult,
    MenuItem,
    Season,
    SeasonalStrategy,
    VatCountry,
)
from .pricing import calculate_restaurant_price_ttc
from .repository import WineCardRepository


SECTION_ORDER = ["sparkling", "white", "rose", "red", "dessert", "fortified"]
COLOR_TO_SECTION = {
    "sparkling": "sparkling",
    "white": "white",
    "rosé": "rose",
    "rose": "rose",
    "red": "red",
    "dessert": "dessert",
    "fortified": "fortified",
}

SEASONAL_STRATEGIES = {
    Season.SUMMER: SeasonalStrategy(
        focus=["rose", "sparkling", "white", "light red"],
        avoid=["heavy red", "fortified"],
        notes="Prioritize freshness and terrace-friendly wines.",
    ),
    Season.WINTER: SeasonalStrategy(
        focus=["full-bodied red", "medium red", "oaky white", "fortified", "dessert"],
        avoid=["too much rose"],
        notes="Prioritize richer reds and structured winter pairings.",
    ),
    Season.SPRING: SeasonalStrategy(
        focus=["sparkling", "white", "rose", "light red"],
        avoid=["very heavy red"],
        notes="Balance freshness with a few versatile reds.",
    ),
    Season.AUTUMN: SeasonalStrategy(
        focus=["medium red", "full-bodied red", "oaky white"],
        avoid=["over-weighted summer rose"],
        notes="Emphasize food-pairing structure for seasonal dishes.",
    ),
}


class WineCardService:
    def __init__(self, repository: WineCardRepository):
        self.repository = repository

    async def read_inventory(self, user_id: UUID) -> list[InventoryItem]:
        return await self.repository.read_inventory(user_id=user_id)

    async def export_editable_menu(
        self,
        user_id: UUID,
        season: Season,
        vat_country: VatCountry = VatCountry.LU,
    ) -> MenuExportResult:
        inventory = await self.read_inventory(user_id=user_id)
        menu_items: list[MenuItem] = []

        for item in inventory:
            pricing = calculate_restaurant_price_ttc(
                item.purchase_price_ht,
                vat_country=vat_country,
            )
            section = self._map_section(item.wine_color)
            menu_items.append(
                MenuItem(
                    section=section,
                    vat_country=pricing.vat_country,
                    vat_rate=pricing.vat_rate,
                    wine_id=item.wine_id,
                    producer=item.producer,
                    wine_name=item.wine_name,
                    vintage=item.vintage,
                    region=item.region,
                    appellation=item.appellation,
                    country=item.country,
                    quantity=item.quantity,
                    purchase_price_ht=item.purchase_price_ht,
                    avg_market_price=item.avg_market_price,
                    selling_price_ttc=pricing.selling_price_ttc,
                    glass_price_ttc=pricing.glass_price_ttc,
                )
            )

        menu_items.sort(key=lambda m: (self._section_rank(m.section), m.producer, m.wine_name))
        markdown = self._build_editable_menu_markdown(menu_items, season=season)

        return MenuExportResult(
            season=season,
            vat_country=vat_country,
            items_count=len(menu_items),
            markdown=markdown,
            menu_items=menu_items,
        )

    async def analyze_menu(
        self,
        user_id: UUID,
        season: Season,
        vat_country: VatCountry = VatCountry.LU,
    ) -> MenuAnalysisResult:
        inventory = await self.read_inventory(user_id=user_id)
        strategy = SEASONAL_STRATEGIES[season]

        section_counts = Counter(self._map_section(item.wine_color) for item in inventory)
        missing_categories = [
            section for section in SECTION_ORDER if section_counts.get(section, 0) == 0
        ]

        low_stock_warnings = []
        for item in sorted(inventory, key=lambda i: (i.quantity, i.wine_name)):
            if item.quantity <= 2:
                low_stock_warnings.append(
                    f"{item.producer} — {item.wine_name}: only {item.quantity} bottle(s)"
                )
            if len(low_stock_warnings) >= 10:
                break

        by_the_glass_suggestions = self._build_by_the_glass_suggestions(
            inventory,
            season,
            vat_country=vat_country,
        )

        summary = (
            f"Inventory has {len(inventory)} wines across {len(section_counts)} sections. "
            f"Missing categories: {', '.join(missing_categories) if missing_categories else 'none'}. "
            f"Generated {len(by_the_glass_suggestions)} by-the-glass suggestions for {season.value}."
        )

        return MenuAnalysisResult(
            season=season,
            strategy=strategy,
            summary=summary,
            missing_categories=missing_categories,
            low_stock_warnings=low_stock_warnings,
            by_the_glass_suggestions=by_the_glass_suggestions,
            section_counts=dict(section_counts),
        )

    def _map_section(self, wine_color: str | None) -> str:
        if not wine_color:
            return "white"
        key = wine_color.strip().lower()
        return COLOR_TO_SECTION.get(key, key)

    def _section_rank(self, section: str) -> int:
        try:
            return SECTION_ORDER.index(section)
        except ValueError:
            return len(SECTION_ORDER)

    def _build_by_the_glass_suggestions(
        self,
        inventory: list[InventoryItem],
        season: Season,
        vat_country: VatCountry,
        max_items: int = 6,
    ) -> list[str]:
        focus_sections_by_season = {
            Season.SPRING: ["sparkling", "white", "rose", "red"],
            Season.SUMMER: ["sparkling", "white", "rose", "red"],
            Season.AUTUMN: ["white", "red", "fortified"],
            Season.WINTER: ["white", "red", "fortified", "dessert"],
        }
        preferred_sections = focus_sections_by_season[season]

        candidates = []
        for item in inventory:
            section = self._map_section(item.wine_color)
            if section not in preferred_sections:
                continue
            if item.quantity < 3:
                continue
            pricing = calculate_restaurant_price_ttc(
                item.purchase_price_ht,
                vat_country=vat_country,
            )
            score = item.quantity
            if section in ["sparkling", "white", "red"]:
                score += 2
            if pricing.glass_price_ttc <= 14:
                score += 1
            candidates.append((score, item, pricing))

        candidates.sort(key=lambda row: row[0], reverse=True)
        suggestions: list[str] = []
        for _, item, pricing in candidates[:max_items]:
            suggestions.append(
                f"{item.producer} — {item.wine_name} ({self._map_section(item.wine_color)}): "
                f"€{pricing.glass_price_ttc:.2f} glass / €{pricing.selling_price_ttc:.2f} bottle"
            )
        return suggestions

    def _build_editable_menu_markdown(self, menu_items: list[MenuItem], season: Season) -> str:
        lines: list[str] = []
        vat_country = menu_items[0].vat_country.value if menu_items else VatCountry.LU.value
        vat_rate = menu_items[0].vat_rate if menu_items else 0.17
        lines.append(f"# Chimerai Bistro Wine Menu — {season.value.title()}")
        lines.append("")
        lines.append("## Editable Wine List")
        lines.append("")
        lines.append(
            "_Prices are editable. Generated from current stock and recommended pricing rules._"
        )
        lines.append(f"_VAT country: {vat_country} ({round(vat_rate * 100)}%)_")
        lines.append("")

        current_section: str | None = None
        for item in menu_items:
            if item.section != current_section:
                current_section = item.section
                lines.append(f"## {current_section.title()}")
                lines.append("")

            vintage = item.vintage or "NV"
            location_parts = [item.appellation, item.region, item.country]
            location = " / ".join(part for part in location_parts if part)
            lines.append(f"**{item.producer} — {item.wine_name} {vintage}**")
            if location:
                lines.append(location)
            lines.append(f"Stock: {item.quantity} bottle(s)")
            lines.append(f"Bottle: €{item.selling_price_ttc:.2f}")
            lines.append(f"Glass: €{item.glass_price_ttc:.2f}")
            lines.append("")

        return "\n".join(lines)
