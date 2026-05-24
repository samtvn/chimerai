"""Service layer for wine-card pricing, menu export, and analysis."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import re
from uuid import UUID

from .models import (
    InventoryItem,
    MenuAnalysisResult,
    MenuExportResult,
    MenuItem,
    Occasion,
    OneShotMenuResult,
    Season,
    SeasonalStrategy,
    VatCountry,
)
from .pricing import calculate_restaurant_price_ttc
from .repository import WineCardRepository


SECTION_ORDER = ["rose", "sparkling", "white", "red", "dessert", "fortified"]
COLOR_TO_SECTION = {
    "sparkling": "sparkling",
    "white": "white",
    "rosé": "rose",
    "rose": "rose",
    "red": "red",
    "dessert": "dessert",
    "fortified": "fortified",
}

BIG_WINE_MIN_PRICE = 50.0
CHEAP_WINE_MAX_PRICE = 50.0
CHEAP_WINE_LOW_STOCK_THRESHOLD = 2

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

OCCASION_PROFILES = {
    Occasion.CHRISTMAS: {
        "season": Season.WINTER,
        "target_sections": ["sparkling", "white", "red", "dessert", "fortified"],
        "max_per_section": 3,
        "max_total": 12,
        "min_quantity": 2,
        "strategy": SeasonalStrategy(
            focus=["sparkling aperitif", "structured red", "dessert and fortified"],
            avoid=["too many light summer wines"],
            notes="Holiday menu: festive start, richer main-course wines, and sweet finish options.",
        ),
        "pairing_notes": [
            "Start with sparkling wines for aperitif and welcome service.",
            "Keep at least one richer red option for roasted dishes.",
            "Include dessert or fortified ending pairings for holiday menus.",
        ],
    },
    Occasion.VALENTINE: {
        "season": Season.WINTER,
        "target_sections": ["sparkling", "rose", "white", "red"],
        "max_per_section": 3,
        "max_total": 10,
        "min_quantity": 2,
        "strategy": SeasonalStrategy(
            focus=["sparkling", "rose", "elegant white", "silky red"],
            avoid=["aggressive tannic-heavy list"],
            notes="Valentine menu: elegant, romantic profile with strong by-the-glass potential.",
        ),
        "pairing_notes": [
            "Prioritize elegant sparkling and rose options for couples.",
            "Balance white and red selections for multi-course flexibility.",
            "Keep pricing smooth for by-the-glass upsell moments.",
        ],
    },
    Occasion.EASTER: {
        "season": Season.SPRING,
        "target_sections": ["sparkling", "white", "rose", "red"],
        "max_per_section": 3,
        "max_total": 10,
        "min_quantity": 2,
        "strategy": SeasonalStrategy(
            focus=["fresh white", "spring rose", "light red", "sparkling"],
            avoid=["overly heavy winter profile"],
            notes="Easter menu: freshness and spring balance for lamb, fish, and vegetable dishes.",
        ),
        "pairing_notes": [
            "Use fresh white wines for lighter spring starters.",
            "Keep one versatile red for lamb or grilled mains.",
            "Sparkling options work well for brunch-style Easter service.",
        ],
    },
    Occasion.BANQUET: {
        "season": Season.AUTUMN,
        "target_sections": ["sparkling", "white", "red", "fortified"],
        "max_per_section": 4,
        "max_total": 14,
        "min_quantity": 3,
        "strategy": SeasonalStrategy(
            focus=["reliable volume wines", "structured red", "versatile white"],
            avoid=["very low stock references"],
            notes="Banquet menu: favor operationally safe wines with enough stock depth.",
        ),
        "pairing_notes": [
            "Prioritize wines with stronger stock depth for large tables.",
            "Keep white/red balance for broad guest preferences.",
            "Reserve fortified options for curated dessert/cheese service.",
        ],
    },
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
        restaurant_name: str = "Chimerai Bistro",
    ) -> MenuExportResult:
        inventory = await self.read_inventory(user_id=user_id)
        selected_inventory, _, _, _, _ = self._select_inventory_for_season(inventory, season)
        return self._build_menu_export_from_inventory(
            inventory=selected_inventory,
            season=season,
            vat_country=vat_country,
            restaurant_name=restaurant_name,
        )

    async def analyze_menu(
        self,
        user_id: UUID,
        season: Season,
        vat_country: VatCountry = VatCountry.LU,
    ) -> MenuAnalysisResult:
        inventory = await self.read_inventory(user_id=user_id)
        return self._build_menu_analysis_from_inventory(
            inventory=inventory,
            season=season,
            vat_country=vat_country,
        )

    async def generate_one_shot_menu(
        self,
        user_id: UUID,
        occasion: Occasion,
        vat_country: VatCountry = VatCountry.LU,
        service_count: int = 3,
        menu_total_price_ttc: float | None = None,
        restaurant_name: str = "Chimerai Bistro",
    ) -> OneShotMenuResult:
        inventory = await self.read_inventory(user_id=user_id)
        profile = OCCASION_PROFILES[occasion]
        season: Season = profile["season"]
        by_glass_mode = occasion != Occasion.BANQUET
        if service_count < 3:
            service_count = 3
        if service_count > 5:
            service_count = 5

        selected_inventory = self._select_inventory_for_occasion(
            inventory=inventory,
            target_sections=profile["target_sections"],
            max_per_section=profile["max_per_section"],
            max_total=profile["max_total"],
            min_quantity=profile["min_quantity"],
        )

        if not selected_inventory and inventory:
            selected_inventory = sorted(
                inventory,
                key=lambda i: (i.quantity, i.purchase_price_ht),
                reverse=True,
            )[: profile["max_total"]]

        menu_export = self._build_menu_export_from_inventory(
            inventory=selected_inventory,
            season=season,
            vat_country=vat_country,
            restaurant_name=restaurant_name,
        )
        menu_analysis = self._build_menu_analysis_from_inventory(
            inventory=selected_inventory,
            season=season,
            vat_country=vat_country,
            strategy_override=profile["strategy"],
        )

        if by_glass_mode:
            menu_analysis.by_the_glass_suggestions = self._build_by_the_glass_suggestions(
                selected_inventory,
                season,
                vat_country=vat_country,
                max_items=service_count,
            )

        suggested_pairing_price_ttc, suggested_per_service_price_ttc = self._compute_pairing_budget(
            menu_total_price_ttc=menu_total_price_ttc,
            service_count=service_count,
            by_glass_mode=by_glass_mode,
        )

        summary = (
            f"Generated one-shot {occasion.value} menu with {len(selected_inventory)} wines "
            f"from {len(inventory)} inventory candidates. "
            f"Mode: {'by-the-glass' if by_glass_mode else 'banquet/bottle-focused'}."
        )
        if by_glass_mode:
            summary += f" Service format: {service_count} services + {service_count} wines."
        if suggested_pairing_price_ttc is not None:
            summary += f" Suggested pairing price: €{suggested_pairing_price_ttc:.2f} TTC."

        return OneShotMenuResult(
            occasion=occasion,
            season=season,
            vat_country=vat_country,
            by_glass_mode=by_glass_mode,
            service_count=service_count,
            menu_total_price_ttc=menu_total_price_ttc,
            suggested_pairing_price_ttc=suggested_pairing_price_ttc,
            suggested_per_service_price_ttc=suggested_per_service_price_ttc,
            inventory_candidates=len(inventory),
            selected_items=len(selected_inventory),
            summary=summary,
            llm_prompt=self._build_one_shot_llm_prompt(
                occasion=occasion,
                season=season,
                by_glass_mode=by_glass_mode,
                service_count=service_count,
                menu_total_price_ttc=menu_total_price_ttc,
                suggested_pairing_price_ttc=suggested_pairing_price_ttc,
                suggested_per_service_price_ttc=suggested_per_service_price_ttc,
                menu_export=menu_export,
            ),
            pairing_notes=profile["pairing_notes"],
            menu_export=menu_export,
            menu_analysis=menu_analysis,
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

    def _normalize_wine_key(self, item: InventoryItem) -> str:
        producer = (item.producer or "").strip().lower()
        wine_name = (item.wine_name or "").strip().lower()
        return f"{producer}::{wine_name}"

    def _parse_vintage_year(self, vintage: str | None) -> int | None:
        if not vintage:
            return None
        match = re.search(r"(19|20)\d{2}", vintage)
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def _vintage_sort_key(self, item: InventoryItem) -> tuple[int, int, float]:
        year = self._parse_vintage_year(item.vintage)
        year_key = year if year is not None else 9999
        return (year_key, -item.quantity, -item.purchase_price_ht)

    def _collapse_to_oldest_vintages(
        self,
        inventory: list[InventoryItem],
    ) -> tuple[list[InventoryItem], list[str]]:
        grouped: dict[str, list[InventoryItem]] = {}
        for item in inventory:
            grouped.setdefault(self._normalize_wine_key(item), []).append(item)

        selected: list[InventoryItem] = []
        duplicate_alerts: list[str] = []

        for candidates in grouped.values():
            candidates_sorted = sorted(candidates, key=self._vintage_sort_key)
            selected_item = candidates_sorted[0]
            selected.append(selected_item)

            has_multiple_vintages = len(candidates_sorted) > 1
            has_big_wine = any(
                c.purchase_price_ht >= BIG_WINE_MIN_PRICE
                or (c.avg_market_price or 0.0) >= BIG_WINE_MIN_PRICE
                for c in candidates_sorted
            )
            if has_multiple_vintages and has_big_wine:
                vintage_labels = [c.vintage or "NV" for c in candidates_sorted]
                duplicate_alerts.append(
                    f"{selected_item.producer} — {selected_item.wine_name}: vintages "
                    f"{', '.join(vintage_labels)} available. Oldest ({selected_item.vintage or 'NV'}) "
                    "was selected. Include multiple vintages?"
                )

        selected.sort(key=lambda i: (self._section_rank(self._map_section(i.wine_color)), i.producer, i.wine_name))
        return selected, duplicate_alerts

    def _build_cheap_low_stock_alerts(self, inventory: list[InventoryItem]) -> list[str]:
        alerts: list[str] = []
        for item in sorted(inventory, key=lambda i: (i.quantity, i.purchase_price_ht, i.wine_name)):
            if item.purchase_price_ht >= CHEAP_WINE_MAX_PRICE:
                continue
            if item.quantity >= CHEAP_WINE_LOW_STOCK_THRESHOLD:
                continue
            alerts.append(
                f"{item.producer} — {item.wine_name}: €{item.purchase_price_ht:.2f} HT, "
                f"{item.quantity} bottle(s) left. Replenish and consider reprinting menu."
            )
            if len(alerts) >= 20:
                break
        return alerts

    def _focus_sections(self, strategy: SeasonalStrategy) -> set[str]:
        focus = " ".join(strategy.focus).lower()
        sections: set[str] = set()
        if "rose" in focus or "rosé" in focus:
            sections.add("rose")
        if "sparkling" in focus:
            sections.add("sparkling")
        if "white" in focus:
            sections.add("white")
        if "red" in focus:
            sections.add("red")
        if "dessert" in focus:
            sections.add("dessert")
        if "fortified" in focus:
            sections.add("fortified")
        return sections

    def _seasonal_score(
        self,
        item: InventoryItem,
        season: Season,
        focus_sections: set[str],
    ) -> float:
        section = self._map_section(item.wine_color)
        score = float(item.quantity) * 2.0
        score += item.purchase_price_ht * 0.08
        if item.avg_market_price:
            score += item.avg_market_price * 0.03
        if section in focus_sections:
            score += 3.0
        year = self._parse_vintage_year(item.vintage)
        if year is not None:
            # Older vintages are preferred when multiple references compete.
            score += max(0.0, float(datetime.utcnow().year - year) * 0.18)
        if item.quantity < 2:
            score -= 1.5
        if season == Season.SUMMER and section in {"rose", "sparkling", "white"}:
            score += 1.0
        if season == Season.WINTER and section in {"red", "fortified", "dessert"}:
            score += 1.0
        return score

    def _compute_menu_max_total(self, candidate_count: int) -> int:
        if candidate_count <= 55:
            return candidate_count
        return min(candidate_count, min(56, max(40, round(candidate_count * 0.70))))

    def _compute_section_targets(
        self,
        available_by_section: dict[str, int],
        max_total: int,
        season: Season,
    ) -> dict[str, int]:
        base_weights = {
            "rose": 0.14,
            "sparkling": 0.14,
            "white": 0.22,
            "red": 0.32,
            "dessert": 0.09,
            "fortified": 0.09,
        }
        season_bump = {
            Season.SPRING: {"rose": 0.05, "sparkling": 0.04, "white": 0.04, "red": -0.09, "dessert": -0.02, "fortified": -0.02},
            Season.SUMMER: {"rose": 0.05, "sparkling": 0.05, "white": 0.06, "red": -0.10, "dessert": -0.03, "fortified": -0.03},
            Season.AUTUMN: {"red": 0.06, "white": 0.03, "rose": -0.04, "sparkling": -0.03, "dessert": -0.01, "fortified": -0.01},
            Season.WINTER: {"red": 0.08, "white": 0.03, "fortified": 0.04, "dessert": 0.04, "rose": -0.08, "sparkling": -0.06},
        }[season]

        weighted: dict[str, float] = {}
        for section in SECTION_ORDER:
            if available_by_section.get(section, 0) <= 0:
                continue
            weighted[section] = max(0.02, base_weights[section] + season_bump.get(section, 0.0))

        total_weight = sum(weighted.values()) or 1.0
        raw_targets = {section: (max_total * weight / total_weight) for section, weight in weighted.items()}
        targets = {section: min(available_by_section[section], int(raw_targets[section])) for section in raw_targets}

        # Ensure at least one reference for present sections when possible.
        sections_present = [s for s in SECTION_ORDER if available_by_section.get(s, 0) > 0]
        if max_total >= len(sections_present):
            for section in sections_present:
                targets[section] = max(1, targets.get(section, 0))

        current_total = sum(targets.values())
        remainders = sorted(
            ((section, raw_targets[section] - targets[section]) for section in targets),
            key=lambda row: row[1],
            reverse=True,
        )
        idx = 0
        while current_total < max_total and remainders:
            section = remainders[idx % len(remainders)][0]
            if targets[section] < available_by_section[section]:
                targets[section] += 1
                current_total += 1
            idx += 1
            if idx > 2000:
                break

        return targets

    def _select_inventory_for_season(
        self,
        inventory: list[InventoryItem],
        season: Season,
        strategy_override: SeasonalStrategy | None = None,
    ) -> tuple[list[InventoryItem], int, list[str], list[str], bool]:
        strategy = strategy_override or SEASONAL_STRATEGIES[season]
        collapsed_inventory, duplicate_vintage_alerts = self._collapse_to_oldest_vintages(inventory)
        total_candidates = len(collapsed_inventory)
        if not collapsed_inventory:
            return [], 0, duplicate_vintage_alerts, [], False

        cheap_low_stock_alerts = self._build_cheap_low_stock_alerts(inventory)
        reprint_menu_recommended = len(cheap_low_stock_alerts) > 0

        max_total = self._compute_menu_max_total(total_candidates)
        focus_sections = self._focus_sections(strategy)

        section_buckets: dict[str, list[InventoryItem]] = {section: [] for section in SECTION_ORDER}
        for item in collapsed_inventory:
            section_buckets.setdefault(self._map_section(item.wine_color), []).append(item)

        for section, items in section_buckets.items():
            items.sort(
                key=lambda i: self._seasonal_score(i, season=season, focus_sections=focus_sections),
                reverse=True,
            )

        available_by_section = {section: len(items) for section, items in section_buckets.items() if items}
        section_targets = self._compute_section_targets(available_by_section, max_total=max_total, season=season)

        selected: list[InventoryItem] = []
        selected_ids: set[int] = set()
        for section in SECTION_ORDER:
            target = section_targets.get(section, 0)
            if target <= 0:
                continue
            for item in section_buckets.get(section, [])[:target]:
                if item.wine_id in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item.wine_id)
                if len(selected) >= max_total:
                    break
            if len(selected) >= max_total:
                break

        if len(selected) < max_total:
            remainder = sorted(
                [item for item in collapsed_inventory if item.wine_id not in selected_ids],
                key=lambda i: self._seasonal_score(i, season=season, focus_sections=focus_sections),
                reverse=True,
            )
            for item in remainder:
                selected.append(item)
                if len(selected) >= max_total:
                    break

        selected.sort(key=lambda i: (self._section_rank(self._map_section(i.wine_color)), i.producer, i.wine_name))
        return selected, total_candidates, duplicate_vintage_alerts[:12], cheap_low_stock_alerts[:12], reprint_menu_recommended

    def _build_menu_export_from_inventory(
        self,
        inventory: list[InventoryItem],
        season: Season,
        vat_country: VatCountry,
        restaurant_name: str,
    ) -> MenuExportResult:
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
        markdown = self._build_editable_menu_markdown(
            menu_items,
            season=season,
            restaurant_name=restaurant_name,
        )

        return MenuExportResult(
            season=season,
            vat_country=vat_country,
            items_count=len(menu_items),
            markdown=markdown,
            menu_items=menu_items,
        )

    def _build_menu_analysis_from_inventory(
        self,
        inventory: list[InventoryItem],
        season: Season,
        vat_country: VatCountry,
        strategy_override: SeasonalStrategy | None = None,
    ) -> MenuAnalysisResult:
        strategy = strategy_override or SEASONAL_STRATEGIES[season]
        selected_inventory, total_candidates, duplicate_vintage_alerts, cheap_low_stock_alerts, reprint_menu_recommended = (
            self._select_inventory_for_season(
                inventory=inventory,
                season=season,
                strategy_override=strategy_override,
            )
        )

        section_counts = Counter(self._map_section(item.wine_color) for item in selected_inventory)
        missing_categories = [section for section in SECTION_ORDER if section_counts.get(section, 0) == 0]

        low_stock_warnings = []
        for item in sorted(selected_inventory, key=lambda i: (i.quantity, i.wine_name)):
            if item.quantity <= 2:
                low_stock_warnings.append(f"{item.producer} — {item.wine_name}: only {item.quantity} bottle(s)")
            if len(low_stock_warnings) >= 10:
                break

        by_the_glass_suggestions = self._build_by_the_glass_suggestions(
            selected_inventory,
            season,
            vat_country=vat_country,
        )

        summary = (
            f"Inventory has {total_candidates} unique references; selected {len(selected_inventory)} for current menu. "
            f"Menu spans {len(section_counts)} sections. "
            f"Missing categories: {', '.join(missing_categories) if missing_categories else 'none'}. "
            f"Generated {len(by_the_glass_suggestions)} by-the-glass suggestions for {season.value}."
        )

        return MenuAnalysisResult(
            season=season,
            strategy=strategy,
            summary=summary,
            selected_for_menu=len(selected_inventory),
            total_inventory_candidates=total_candidates,
            missing_categories=missing_categories,
            low_stock_warnings=low_stock_warnings,
            cheap_wine_low_stock_alerts=cheap_low_stock_alerts,
            duplicate_vintage_alerts=duplicate_vintage_alerts,
            reprint_menu_recommended=reprint_menu_recommended,
            by_the_glass_suggestions=by_the_glass_suggestions,
            section_counts=dict(section_counts),
        )

    def _select_inventory_for_occasion(
        self,
        inventory: list[InventoryItem],
        target_sections: list[str],
        max_per_section: int,
        max_total: int,
        min_quantity: int,
    ) -> list[InventoryItem]:
        collapsed_inventory, _ = self._collapse_to_oldest_vintages(inventory)
        grouped: dict[str, list[InventoryItem]] = {section: [] for section in target_sections}
        for item in collapsed_inventory:
            section = self._map_section(item.wine_color)
            if section in grouped and item.quantity >= min_quantity:
                grouped[section].append(item)

        selected: list[InventoryItem] = []
        selected_ids: set[int] = set()
        for section in target_sections:
            candidates = sorted(
                grouped[section],
                key=lambda i: (i.quantity, i.purchase_price_ht),
                reverse=True,
            )
            for item in candidates[:max_per_section]:
                if item.wine_id in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item.wine_id)
                if len(selected) >= max_total:
                    return selected

        remaining = sorted(
            [item for item in collapsed_inventory if item.wine_id not in selected_ids],
            key=lambda i: (i.quantity, i.purchase_price_ht),
            reverse=True,
        )
        for item in remaining:
            selected.append(item)
            if len(selected) >= max_total:
                break
        return selected

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

    def _build_editable_menu_markdown(
        self,
        menu_items: list[MenuItem],
        season: Season,
        restaurant_name: str,
    ) -> str:
        lines: list[str] = []
        vat_country = menu_items[0].vat_country.value if menu_items else VatCountry.LU.value
        vat_rate = menu_items[0].vat_rate if menu_items else 0.17
        lines.append(f"# {restaurant_name}")
        lines.append("")
        lines.append(f"## Wine Menu — {season.value.title()}")
        lines.append("")
        lines.append("## Editable Wine List")
        lines.append("")
        lines.append(
            "_Prices are editable. Generated from current cellar selection and pricing rules._"
        )
        lines.append(f"_VAT country: {vat_country} ({round(vat_rate * 100)}%)_")
        lines.append("_Glass serving volume: 12cl • Bottle volume: 75cl_")
        lines.append("")

        section_title = {
            "rose": "Rosé",
            "sparkling": "Sparkling",
            "white": "White",
            "red": "Red",
            "dessert": "Dessert",
            "fortified": "Fortified",
        }

        for section in SECTION_ORDER:
            section_items = [item for item in menu_items if item.section == section]
            if not section_items:
                continue
            lines.append(f"## {section_title.get(section, section.title())}")
            lines.append("")
            lines.append("| Wine | Origin | Vintage | 12cl TTC | Bottle TTC |")
            lines.append("|---|---|:---:|---:|---:|")
            for item in section_items:
                location_parts = [item.appellation, item.region, item.country]
                location = " / ".join(part for part in location_parts if part) or "—"
                vintage = item.vintage or "NV"
                wine_name = f"{item.producer} — {item.wine_name}"
                lines.append(
                    f"| {wine_name} | {location} | {vintage} | €{item.glass_price_ttc:.2f} | €{item.selling_price_ttc:.2f} |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Prix TTC service compris.**")
        lines.append("**L’abus d’alcool est dangereux pour la santé, à consommer avec modération.**")
        lines.append("**La vente d’alcool est interdite aux mineurs.**")

        return "\n".join(lines)

    def _compute_pairing_budget(
        self,
        menu_total_price_ttc: float | None,
        service_count: int,
        by_glass_mode: bool,
    ) -> tuple[float | None, float | None]:
        if not by_glass_mode or menu_total_price_ttc is None:
            return None, None
        if menu_total_price_ttc <= 0:
            return None, None

        ratio_by_services = {
            3: 0.40,
            4: 0.50,
            5: 0.58,
        }
        ratio = ratio_by_services.get(service_count, 0.40)
        pairing_total = round(menu_total_price_ttc * ratio, 2)
        per_service = round(pairing_total / service_count, 2)
        return pairing_total, per_service

    def _build_one_shot_llm_prompt(
        self,
        occasion: Occasion,
        season: Season,
        by_glass_mode: bool,
        service_count: int,
        menu_total_price_ttc: float | None,
        suggested_pairing_price_ttc: float | None,
        suggested_per_service_price_ttc: float | None,
        menu_export: MenuExportResult,
    ) -> str:
        lines = [
            "You are a sommelier assistant for a restaurant wine pairing proposal.",
            f"Occasion: {occasion.value}",
            f"Season: {season.value}",
            f"Mode: {'by-the-glass' if by_glass_mode else 'banquet / bottle-focused'}",
            f"Inventory candidates selected: {menu_export.items_count}",
        ]
        if by_glass_mode:
            lines.append(f"Target format: {service_count} services + {service_count} wines.")
        if menu_total_price_ttc is not None:
            lines.append(f"Customer menu total price: €{menu_total_price_ttc:.2f} TTC.")
        if suggested_pairing_price_ttc is not None:
            lines.append(f"Target wine pairing price: €{suggested_pairing_price_ttc:.2f} TTC.")
        if suggested_per_service_price_ttc is not None:
            lines.append(f"Target per-service wine allocation: €{suggested_per_service_price_ttc:.2f} TTC.")

        lines.extend(
            [
                "",
                "Instructions:",
                "1) Build a coherent pairing progression (aperitif -> starter -> main -> dessert if relevant).",
                "2) Keep wine choices within the selected inventory and mention substitutions if stock risk exists.",
                "3) Explain why each wine matches the dish style and occasion.",
                "4) Keep pricing aligned with the pairing target when provided.",
                "5) Keep legal footer lines for pricing/service and responsible alcohol consumption.",
                "",
                "Editable menu markdown is provided separately as source of available wines.",
            ]
        )
        return "\n".join(lines)
