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
    """Core application service for Wine Card generation and analysis.

    This service orchestrates inventory reads, seasonal filtering, pricing,
    menu export formatting, and trigger-oriented strategy analysis.
    """

    def __init__(self, repository: WineCardRepository):
        """Create a service instance bound to a repository.

        Args:
            repository: Data access object used to read inventory inputs.
        """
        self.repository = repository

    async def read_inventory(self, user_id: UUID) -> list[InventoryItem]:
        """Load current inventory rows for a user.

        Args:
            user_id: Target restaurant user identifier.

        Returns:
            Normalized inventory items with quantity and pricing inputs.
        """
        return await self.repository.read_inventory(user_id=user_id)

    async def export_editable_menu(
        self,
        user_id: UUID,
        season: Season,
        vat_country: VatCountry = VatCountry.LU,
        restaurant_name: str = "Chimerai Bistro",
    ) -> MenuExportResult:
        """Generate an editable seasonal menu markdown + structured rows.

        Business Rules:
            - Inventory is season-filtered before pricing/export.
            - Export ordering is section-first with display-mode hints.

        Args:
            user_id: Target restaurant user identifier.
            season: Seasonal profile used for filtering and weighting.
            vat_country: VAT context for TTC computation.
            restaurant_name: Header label used in exported markdown.

        Returns:
            Fully rendered menu export payload.
        """
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
        """Run strategy analysis for a seasonal menu selection.

        Args:
            user_id: Target restaurant user identifier.
            season: Seasonal profile used for curation strategy.
            vat_country: VAT context used by by-the-glass suggestions.

        Returns:
            Strategy summary including gaps, alerts, and section counts.
        """
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
        """Create a one-shot event menu for a specific occasion.

        Business Rules:
            - Non-banquet occasions default to by-the-glass mode.
            - Service count is normalized to a 4-5 service style (bounded 3..5).
            - Selection prioritizes operational stock and section quotas.

        Args:
            user_id: Target restaurant user identifier.
            occasion: Event profile driving season and section targets.
            vat_country: VAT context for all TTC prices.
            service_count: Desired number of services for pairing progression.
            menu_total_price_ttc: Optional customer menu total used for budget hints.
            restaurant_name: Header label used in exported markdown.

        Returns:
            One-shot result with export, analysis, pairing notes, and prompt text.
        """
        inventory = await self.read_inventory(user_id=user_id)
        profile = OCCASION_PROFILES[occasion]
        season: Season = profile["season"]
        by_glass_mode = occasion != Occasion.BANQUET
        service_count = max(3, min(5, service_count))
        suggested_pairing_price_ttc, suggested_per_service_price_ttc = self._compute_pairing_budget(
            menu_total_price_ttc=menu_total_price_ttc,
            service_count=service_count,
            by_glass_mode=by_glass_mode,
        )

        # For by-the-glass one-shot menus we want a very short list: one wine per service
        # so cap total results to `service_count` and prefer at most one per section.
        if by_glass_mode:
            soft_max_glass_price = None
            if suggested_per_service_price_ttc is not None:
                soft_max_glass_price = round(suggested_per_service_price_ttc * 1.25, 2)
            selected_inventory = self._select_inventory_for_occasion(
                inventory=inventory,
                target_sections=profile["target_sections"],
                max_per_section=1,
                max_total=service_count,
                min_quantity=profile["min_quantity"],
                vat_country=vat_country,
                max_total_glass_price_ttc=suggested_pairing_price_ttc,
                soft_max_glass_price_ttc=soft_max_glass_price,
            )
        else:
            selected_inventory = self._select_inventory_for_occasion(
                inventory=inventory,
                target_sections=profile["target_sections"],
                max_per_section=profile["max_per_section"],
                max_total=profile["max_total"],
                min_quantity=profile["min_quantity"],
                vat_country=vat_country,
            )

            # If by-the-glass mode, enforce a curated glass-first selection with
            # limited slots per section and include style constraints (oaky / non-oak)
            if by_glass_mode:
                # limits for glass refs: 1 rose, 1 sparkling, 2 red, 2 white, 1 dessert
                glass_limits = {"rose": 1, "sparkling": 1, "red": 2, "white": 2, "dessert": 1}

                def is_oaky(item: InventoryItem) -> bool:
                    text = " ".join([str(item.wine_name or ""), str(item.grape_variety or "")]).lower()
                    oak_keys = ("oak", "oaky", "boisé", "boise", "barrel", "barrique")
                    return any(k in text for k in oak_keys)

                # candidates for glass: enough quantity and plausible glass pricing
                glass_candidates = []
                bottle_candidates = []
                for it in selected_inventory:
                    # treat dessert/fortified as dessert section when present
                    sec = self._map_section(it.wine_color)
                    # prefer items with at least 2 bottles for glass service
                    if it.quantity >= 2:
                        glass_candidates.append((sec, it))
                    else:
                        bottle_candidates.append((sec, it))

                chosen_glass: list[InventoryItem] = []
                chosen_ids = set()

                # First try to satisfy explicit section quotas
                for section, limit in glass_limits.items():
                    cands = [it for sec, it in glass_candidates if sec == section and it.wine_id not in chosen_ids]
                    # prefer non-oaky for white/rose, and include at least one oaky if strategy requests
                    if section in ("white", "rose"):
                        non_oaky = [it for it in cands if not is_oaky(it)]
                        use = non_oaky[:limit] or cands[:limit]
                    else:
                        use = cands[:limit]
                    for it in use:
                        chosen_glass.append(it)
                        chosen_ids.add(it.wine_id)

                # Ensure a dessert sweet option if available
                if not any(self._map_section(i.wine_color) == "dessert" for i in chosen_glass):
                    dess = [it for sec, it in glass_candidates if sec == "dessert" and it.wine_id not in chosen_ids]
                    if dess:
                        chosen_glass.append(dess[0])
                        chosen_ids.add(dess[0].wine_id)

                # Fill remaining glass slots up to service_count if still below
                remaining_slots = max(0, service_count - len(chosen_glass))
                if remaining_slots > 0:
                    rest = [it for sec, it in glass_candidates if it.wine_id not in chosen_ids]
                    for it in rest[:remaining_slots]:
                        chosen_glass.append(it)
                        chosen_ids.add(it.wine_id)

                # Prepare final selected inventory: chosen_glass first (marked as glass), then others
                final_selected: list[InventoryItem] = []
                for g in chosen_glass:
                    final_selected.append(g)
                for it in selected_inventory:
                    if it.wine_id not in chosen_ids:
                        final_selected.append(it)

                selected_inventory = final_selected

        if not selected_inventory and inventory:
            selected_inventory = sorted(
                inventory,
                key=lambda i: (i.quantity, i.purchase_price_ht),
                reverse=True,
            )[: profile["max_total"]]

        selected_glass_total_ttc = self._compute_glass_total_ttc(
            selected_inventory,
            vat_country=vat_country,
        )

        menu_export = self._build_menu_export_from_inventory(
            inventory=selected_inventory,
            season=season,
            vat_country=vat_country,
            restaurant_name=restaurant_name,
            one_shot_layout=True,
            one_shot_title=self._build_one_shot_card_title(occasion),
            one_shot_forfait_total_ttc=selected_glass_total_ttc,
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

        summary = (
            f"Generated one-shot {occasion.value} menu with {len(selected_inventory)} wines "
            f"from {len(inventory)} inventory candidates. "
            f"Mode: {'by-the-glass' if by_glass_mode else 'banquet/bottle-focused'}."
        )
        if by_glass_mode:
            summary += f" Service format: {service_count} services + {service_count} wines."
            summary += f" Selected glass total: €{selected_glass_total_ttc:.2f} TTC."
        if suggested_pairing_price_ttc is not None:
            summary += f" Suggested pairing price: €{suggested_pairing_price_ttc:.2f} TTC."
            if selected_glass_total_ttc > suggested_pairing_price_ttc:
                summary += " Budget alert: selected wines exceed target; review one expensive reference."

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
        # Penalize heavy/full-bodied reds in summer to avoid overly warm-profile lists
        if season == Season.SUMMER and section == "red":
            heavy_keywords = ("full", "full-bodied", "full bodied", "heavy", "robust", "powerful", "bold")
            text = "".join([str(item.wine_name or ""), " ", str(item.grape_variety or "")]).lower()
            if any(k in text for k in heavy_keywords):
                score -= 3.0
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

        # Enforce season-specific caps: limit rosé exposure in winter to 2-3 refs
        if season == Season.WINTER and "rose" in targets:
            targets["rose"] = min(targets["rose"], 3)

        return targets


    def _select_inventory_for_season(
        self,
        inventory: list[InventoryItem],
        season: Season,
        strategy_override: SeasonalStrategy | None = None,
    ) -> tuple[list[InventoryItem], int, list[str], list[str], bool]:
        """Select seasonal references from inventory using weighted curation.

        Args:
            inventory: Raw inventory rows, potentially containing duplicate vintages.
            season: Seasonal profile used for scoring and section targets.
            strategy_override: Optional occasion-specific strategy replacement.

        Returns:
            Tuple containing:
                - selected inventory references for the menu
                - total unique candidate count after vintage collapsing
                - duplicate-vintage alerts
                - cheap/low-stock alerts
                - whether menu reprint should be considered
        """
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
        one_shot_layout: bool = False,
        one_shot_title: str | None = None,
        one_shot_forfait_total_ttc: float | None = None,
    ) -> MenuExportResult:
        """Build the menu export payload from a preselected inventory set.

        Side Effects:
            None. This method is deterministic for a given input list.

        Args:
            inventory: Curated references to render.
            season: Season label for the menu title.
            vat_country: VAT context for TTC prices.
            restaurant_name: Header name used in markdown output.

        Returns:
            Structured export containing markdown and menu row details.
        """
        menu_items: list[MenuItem] = []
        # Split inventory into by-the-glass candidates (front) and bottle-only (back)
        glass_items: list[MenuItem] = []
        bottle_items: list[MenuItem] = []
        for item in inventory:
            pricing = calculate_restaurant_price_ttc(
                item.purchase_price_ht,
                vat_country=vat_country,
            )
            section = self._map_section(item.wine_color)
            menu_item = MenuItem(
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
                display_mode="both",
            )

            # Determine if this should be presented as glass-first candidate.
            # Heuristic: enough stock for glass service and glass price sensible.
            if item.quantity >= 2 and pricing.glass_price_ttc is not None:
                menu_item.display_mode = "glass"
                glass_items.append(menu_item)
            else:
                menu_item.display_mode = "bottle"
                bottle_items.append(menu_item)

        # Final ordering: glass-first then bottle.
        menu_items = glass_items + bottle_items
        menu_items.sort(
            key=lambda m: (
                0 if m.display_mode == "glass" else 1,
                self._section_rank(m.section),
                m.producer,
                m.wine_name,
            )
        )
        if one_shot_layout:
            markdown = self._build_one_shot_menu_markdown(
                menu_items,
                season=season,
                restaurant_name=restaurant_name,
                one_shot_title=one_shot_title,
                one_shot_forfait_total_ttc=one_shot_forfait_total_ttc,
            )
        else:
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
        """Compute strategy diagnostics for a seasonal menu candidate set.

        Args:
            inventory: Raw inventory rows before seasonal reduction.
            season: Seasonal profile used for curation.
            vat_country: VAT context for glass/bottle suggestion pricing.
            strategy_override: Optional occasion profile strategy.

        Returns:
            Full analysis object used by the Wine Strategy Check UI.
        """
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
        seasonal_inventory_guidance = self._build_seasonal_inventory_guidance(
            selected_inventory,
            season,
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
            seasonal_inventory_guidance=seasonal_inventory_guidance,
            cheap_wine_low_stock_alerts=cheap_low_stock_alerts,
            duplicate_vintage_alerts=duplicate_vintage_alerts,
            reprint_menu_recommended=reprint_menu_recommended,
            by_the_glass_suggestions=by_the_glass_suggestions,
            section_counts=dict(section_counts),
        )

    def _build_seasonal_inventory_guidance(
        self,
        selected_inventory: list[InventoryItem],
        season: Season,
    ) -> list[str]:
        """Generate short operator guidance from seasonal inventory composition."""
        if not selected_inventory:
            return [
                f"{season.value.title()} menu has no selected wines yet. Re-run curation after inventory refresh."
            ]

        section_stock: Counter[str] = Counter()
        section_refs: Counter[str] = Counter()
        low_stock_refs: Counter[str] = Counter()
        for item in selected_inventory:
            section = self._map_section(item.wine_color)
            section_stock[section] += item.quantity
            section_refs[section] += 1
            if item.quantity <= 2:
                low_stock_refs[section] += 1

        guidance: list[str] = []

        rose_stock = section_stock.get("rose", 0)
        rose_refs = section_refs.get("rose", 0)
        if season in {Season.AUTUMN, Season.WINTER} and rose_stock <= 3:
            guidance.append(
                f"{season.value.title()} menu: rose stock is low ({rose_stock} bottles / {rose_refs} refs), which is normal for the season. Keep current stock, no urgent purchase."
            )
        elif season in {Season.SPRING, Season.SUMMER} and rose_stock <= 3:
            guidance.append(
                f"{season.value.title()} menu: rose stock is low ({rose_stock} bottles / {rose_refs} refs). Consider buying 1-2 versatile rose references."
            )

        red_stock = section_stock.get("red", 0)
        if season == Season.WINTER and red_stock < 8:
            guidance.append(
                f"Winter service depends on reds, but current red stock is {red_stock} bottles. Replenish structured reds before the next reprint."
            )

        focus_sections_by_season = {
            Season.SPRING: ["sparkling", "white", "rose"],
            Season.SUMMER: ["sparkling", "white", "rose"],
            Season.AUTUMN: ["white", "red"],
            Season.WINTER: ["white", "red", "fortified", "dessert"],
        }
        section_labels = {
            "sparkling": "sparkling",
            "white": "white",
            "rose": "rose",
            "red": "red",
            "dessert": "dessert",
            "fortified": "fortified",
        }
        for section in focus_sections_by_season[season]:
            if section_refs.get(section, 0) == 0:
                guidance.append(
                    f"{season.value.title()} menu is missing {section_labels[section]} references. Add at least one to improve balance."
                )
            elif low_stock_refs.get(section, 0) >= section_refs.get(section, 0):
                guidance.append(
                    f"All selected {section_labels[section]} references are low stock. Keep the style on the menu but plan targeted restock."
                )

        return guidance[:6]

    def _select_inventory_for_occasion(
        self,
        inventory: list[InventoryItem],
        target_sections: list[str],
        max_per_section: int,
        max_total: int,
        min_quantity: int,
        vat_country: VatCountry,
        max_total_glass_price_ttc: float | None = None,
        soft_max_glass_price_ttc: float | None = None,
    ) -> list[InventoryItem]:
        collapsed_inventory, _ = self._collapse_to_oldest_vintages(inventory)
        grouped: dict[str, list[InventoryItem]] = {section: [] for section in target_sections}
        eligible_inventory = [item for item in collapsed_inventory if item.quantity >= min_quantity]
        pricing_by_wine_id: dict[int, float] = {}
        for item in collapsed_inventory:
            section = self._map_section(item.wine_color)
            pricing_by_wine_id[item.wine_id] = calculate_restaurant_price_ttc(
                item.purchase_price_ht,
                vat_country=vat_country,
            ).glass_price_ttc
            if section in grouped and item.quantity >= min_quantity:
                grouped[section].append(item)

        def glass_price(item: InventoryItem) -> float:
            return pricing_by_wine_id.get(item.wine_id, 0.0)

        def select_sort_key(item: InventoryItem) -> tuple[float, float, float]:
            # In budget mode, prioritize affordable glasses first.
            if max_total_glass_price_ttc is not None:
                return (glass_price(item), -float(item.quantity), item.purchase_price_ht)
            return (-float(item.quantity), -item.purchase_price_ht, glass_price(item))

        selected: list[InventoryItem] = []
        selected_ids: set[int] = set()
        running_total = 0.0

        def can_add_candidate(candidate: InventoryItem) -> bool:
            nonlocal running_total
            if max_total_glass_price_ttc is None:
                return True
            candidate_price = glass_price(candidate)
            projected_total = running_total + candidate_price
            if projected_total <= max_total_glass_price_ttc + 0.01:
                return True

            remaining_slots = max_total - (len(selected) + 1)
            if remaining_slots <= 0:
                return projected_total <= max_total_glass_price_ttc + 0.01

            remaining_prices = sorted(
                glass_price(item)
                for item in eligible_inventory
                if item.wine_id not in selected_ids and item.wine_id != candidate.wine_id
            )
            floor_rest = sum(remaining_prices[:remaining_slots])
            return projected_total + floor_rest <= max_total_glass_price_ttc + 0.01

        def add_item(item: InventoryItem):
            nonlocal running_total
            selected.append(item)
            selected_ids.add(item.wine_id)
            running_total += glass_price(item)

        for section in target_sections:
            candidates = sorted(
                grouped[section],
                key=select_sort_key,
            )
            section_added = 0
            for item in candidates:
                if item.wine_id in selected_ids:
                    continue
                if soft_max_glass_price_ttc is not None and glass_price(item) > soft_max_glass_price_ttc:
                    continue
                if not can_add_candidate(item):
                    continue
                add_item(item)
                section_added += 1
                if len(selected) >= max_total:
                    selected.sort(key=lambda i: (self._section_rank(self._map_section(i.wine_color)), i.producer, i.wine_name))
                    return selected
                if section_added >= max_per_section:
                    break

            # If nothing affordable was found in this section, fall back to the cheapest candidate.
            if section_added == 0 and candidates and len(selected) < max_total:
                fallback = candidates[0]
                if fallback.wine_id not in selected_ids:
                    add_item(fallback)
                    if len(selected) >= max_total:
                        selected.sort(key=lambda i: (self._section_rank(self._map_section(i.wine_color)), i.producer, i.wine_name))
                        return selected

        remaining = sorted(
            [item for item in eligible_inventory if item.wine_id not in selected_ids],
            key=select_sort_key,
        )
        for item in remaining:
            if soft_max_glass_price_ttc is not None and glass_price(item) > soft_max_glass_price_ttc:
                continue
            if not can_add_candidate(item):
                continue
            add_item(item)
            if len(selected) >= max_total:
                break

        # If budget constraints were too restrictive, complete the list with cheapest available references.
        if len(selected) < max_total:
            fallback_remaining = sorted(
                [item for item in eligible_inventory if item.wine_id not in selected_ids],
                key=lambda i: (glass_price(i), -float(i.quantity), i.purchase_price_ht),
            )
            for item in fallback_remaining:
                add_item(item)
                if len(selected) >= max_total:
                    break

        # Final budget repair pass: swap expensive picks for cheaper alternatives when possible.
        if max_total_glass_price_ttc is not None and selected:
            selected = self._repair_selection_budget(
                selected=selected,
                candidates=eligible_inventory,
                pricing_by_wine_id=pricing_by_wine_id,
                budget=max_total_glass_price_ttc,
            )

        selected.sort(key=lambda i: (self._section_rank(self._map_section(i.wine_color)), i.producer, i.wine_name))
        return selected

    def _repair_selection_budget(
        self,
        selected: list[InventoryItem],
        candidates: list[InventoryItem],
        pricing_by_wine_id: dict[int, float],
        budget: float,
    ) -> list[InventoryItem]:
        selected = selected[:]
        selected_ids = {item.wine_id for item in selected}

        def price(item: InventoryItem) -> float:
            return pricing_by_wine_id.get(item.wine_id, 0.0)

        current_total = sum(price(item) for item in selected)
        if current_total <= budget + 0.01:
            return selected

        safeguard = 0
        while current_total > budget + 0.01 and safeguard < 50:
            safeguard += 1
            best_swap: tuple[int, InventoryItem, float] | None = None
            for idx, selected_item in enumerate(selected):
                selected_section = self._map_section(selected_item.wine_color)
                selected_price = price(selected_item)
                for cand in candidates:
                    if cand.wine_id in selected_ids:
                        continue
                    cand_price = price(cand)
                    if cand_price >= selected_price:
                        continue
                    # Prefer section-preserving swaps to keep pairing progression coherent.
                    section_bonus = 0.05 if self._map_section(cand.wine_color) == selected_section else 0.0
                    gain = (selected_price - cand_price) + section_bonus
                    if best_swap is None or gain > best_swap[2]:
                        best_swap = (idx, cand, gain)
            if best_swap is None:
                break

            idx, replacement, _ = best_swap
            removed = selected[idx]
            selected_ids.remove(removed.wine_id)
            selected[idx] = replacement
            selected_ids.add(replacement.wine_id)
            current_total = sum(price(item) for item in selected)

        return selected

    def _compute_glass_total_ttc(
        self,
        inventory: list[InventoryItem],
        vat_country: VatCountry,
    ) -> float:
        total = 0.0
        for item in inventory:
            total += calculate_restaurant_price_ttc(
                item.purchase_price_ht,
                vat_country=vat_country,
            ).glass_price_ttc
        return round(total, 2)

    def _build_one_shot_card_title(self, occasion: Occasion) -> str:
        labels = {
            Occasion.CHRISTMAS: "Christmas Special Food Pairing Card",
            Occasion.VALENTINE: "Valentine Special Food Pairing Card",
            Occasion.EASTER: "Easter Special Food Pairing Card",
            Occasion.BANQUET: "Banquet Special Food Pairing Card",
        }
        return labels.get(occasion, "Special Food Pairing Card")

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

        glass_selection = [item for item in menu_items if item.display_mode in ("glass", "both")]
        bottle_selection = [item for item in menu_items if item.display_mode in ("bottle", "both")]

        lines.append("## By-the-Glass Selection")
        lines.append("")
        if glass_selection:
            lines.append("| Wine | Origin | Vintage | 12cl TTC |")
            lines.append("|---|---|:---:|---:|")
            for item in glass_selection:
                location_parts = [item.appellation, item.region, item.country]
                location = " / ".join(part for part in location_parts if part) or "—"
                vintage = item.vintage or "NV"
                wine_name = f"{item.producer} — {item.wine_name}"
                lines.append(f"| {wine_name} | {location} | {vintage} | €{item.glass_price_ttc:.2f} |")
        else:
            lines.append("_No by-the-glass wines currently selected._")
        lines.append("")

        lines.append("## Bottle Selection")
        lines.append("")
        if bottle_selection:
            lines.append("| Wine | Origin | Vintage | Bottle TTC |")
            lines.append("|---|---|:---:|---:|")
            for item in bottle_selection:
                location_parts = [item.appellation, item.region, item.country]
                location = " / ".join(part for part in location_parts if part) or "—"
                vintage = item.vintage or "NV"
                wine_name = f"{item.producer} — {item.wine_name}"
                lines.append(f"| {wine_name} | {location} | {vintage} | €{item.selling_price_ttc:.2f} |")
        else:
            lines.append("_No bottle-only wines currently selected._")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Prix TTC service compris.**")
        lines.append("**L’abus d’alcool est dangereux pour la santé, à consommer avec modération.**")
        lines.append("**La vente d’alcool est interdite aux mineurs.**")

        return "\n".join(lines)

    def _build_one_shot_menu_markdown(
        self,
        menu_items: list[MenuItem],
        season: Season,
        restaurant_name: str,
        one_shot_title: str | None = None,
        one_shot_forfait_total_ttc: float | None = None,
    ) -> str:
        lines: list[str] = []
        vat_country = menu_items[0].vat_country.value if menu_items else VatCountry.LU.value
        vat_rate = menu_items[0].vat_rate if menu_items else 0.17
        lines.append(f"# {restaurant_name}")
        lines.append("")
        lines.append(f"## {one_shot_title or 'Special Food Pairing Card'}")
        lines.append("")
        lines.append(f"_Season: {season.value.title()}_")
        lines.append("")
        lines.append("_Single-event format: wine + 12cl price + concise tasting note._")
        lines.append(f"_VAT country: {vat_country} ({round(vat_rate * 100)}%)_")
        lines.append("")

        if not menu_items:
            lines.append("_No wines selected for this one-shot menu._")
            lines.append("")
        else:
            lines.append("| Wine | Origin | Vintage | Tasting note | 12cl TTC |")
            lines.append("|---|---|:---:|---|---:|")
            for item in menu_items:
                wine_name = f"{item.producer} — {item.wine_name}"
                location_parts = [item.appellation, item.region, item.country]
                location = " / ".join(part for part in location_parts if part) or "—"
                vintage = item.vintage or "NV"
                tasting_note = self._build_tasting_note(item)
                lines.append(
                    f"| {wine_name} | {location} | {vintage} | {tasting_note} | €{item.glass_price_ttc:.2f} |"
                )
            lines.append("")

        if one_shot_forfait_total_ttc is not None:
            lines.append(f"**Forfait accord mets: €{one_shot_forfait_total_ttc:.2f} TTC**")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Prix TTC service compris.**")
        lines.append("**L’abus d’alcool est dangereux pour la santé, à consommer avec modération.**")
        lines.append("**La vente d’alcool est interdite aux mineurs.**")

        return "\n".join(lines)

    def _build_tasting_note(self, item: MenuItem) -> str:
        section = self._map_section(item.section)
        profile_by_section = {
            "sparkling": "Bulles fines, tension citronnee et finale nette a dominante crayeuse.",
            "white": "Noyau de fruits frais, acidite equilibree et trame minerale precise.",
            "rose": "Aromes de petits fruits rouges, belle fraicheur et finale seche et gourmande.",
            "red": "Fruits noirs murs, tanins souples et touche epicee en finale.",
            "dessert": "Fruit bien concentre, douceur soyeuse et acidite vive en soutien.",
            "fortified": "Notes de fruits secs, epices chaudes et structure persistante.",
        }
        base_note = profile_by_section.get(
            section,
            "Profil fruite equilibre, avec de la fraicheur et une finale nette.",
        )
        origin_hint = item.appellation or item.region or item.country
        if origin_hint:
            return f"{base_note} Belle expression de {origin_hint}."
        return base_note

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
        """Compose the briefing prompt for an LLM sommelier assistant.

        Args:
            occasion: Event context used to set tone and constraints.
            season: Seasonal context used for pairing expectations.
            by_glass_mode: Whether the menu is glass-first vs bottle-first.
            service_count: Number of planned services.
            menu_total_price_ttc: Optional customer menu total.
            suggested_pairing_price_ttc: Optional target pairing total.
            suggested_per_service_price_ttc: Optional per-service target.
            menu_export: Current candidate menu export metadata.

        Returns:
            Prompt text encoding constraints and expected output style.
        """
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
                "",
                "Presentation constraints for this one-shot menu:",
                "- Use one-shot layout only: wine name + 12cl price + a short tasting note.",
                "- Do not display bottle prices in the one-shot output.",
                "- By-the-glass limits: 1 sparkling, 1 rosé, up to 2 whites, up to 2 reds, include 1 dessert if possible.",
                "- For by-the-glass choices prefer non-oaky whites/rosés; mark oaky options only as substitutions.",
                "- For each suggested wine, provide a one-line justification (pairing + short tasting note) and indicate substitution if stock risk exists.",
            ]
        )
        return "\n".join(lines)
