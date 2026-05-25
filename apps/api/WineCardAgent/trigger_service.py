"""Trigger service for automatic wine-card refresh and recommendation reporting."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from agents.event_bus import AgentEvent, event_bus
from apps.api.database.database import AsyncReadSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from .models import Season, TriggerReason, VatCountry, WineCardTriggerReport
from .repository import WineCardRepository
from .service import WineCardService


class WineCardTriggerService:
    """Handles manual and event-driven trigger runs for wine-card updates."""

    _latest_report: WineCardTriggerReport | None = None

    @classmethod
    def get_latest_report(cls) -> WineCardTriggerReport | None:
        return cls._latest_report

    @classmethod
    async def run_once(
        cls,
        reason: TriggerReason = TriggerReason.MANUAL,
        season: Season = Season.WINTER,
        vat_country: VatCountry = VatCountry.LU,
        min_stock_threshold: int = 2,
    ) -> WineCardTriggerReport:
        async with AsyncReadSessionLocal() as session:
            user_id = await get_demo_user_id(session)
            service = WineCardService(WineCardRepository(session))
            inventory = await service.read_inventory(user_id)

            low_stock_entries = sorted(
                [item for item in inventory if item.quantity <= min_stock_threshold],
                key=lambda item: (item.quantity, item.wine_name),
            )
            low_stock_items = [
                f"{item.producer} — {item.wine_name} ({item.quantity})"
                for item in low_stock_entries[:20]
            ]

            should_refresh = reason == TriggerReason.MANUAL or len(low_stock_entries) > 0
            should_purchase = len(low_stock_entries) > 0

            menu_export = None
            menu_analysis = None
            if should_refresh:
                menu_export = await service.export_editable_menu(
                    user_id=user_id,
                    season=season,
                    vat_country=vat_country,
                )
                menu_analysis = await service.analyze_menu(
                    user_id=user_id,
                    season=season,
                    vat_country=vat_country,
                )

            procurement_suggestions = cls._build_procurement_suggestions(
                low_stock_items=low_stock_items,
                missing_categories=menu_analysis.missing_categories if menu_analysis else [],
            )
            sales_boost_suggestions = cls._build_sales_boost_suggestions(menu_analysis)
            wine_fair_watchlist = cls._build_wine_fair_watchlist(menu_analysis)

            report = WineCardTriggerReport(
                trigger_reason=reason,
                triggered_at=datetime.now(timezone.utc),
                season=season,
                vat_country=vat_country,
                min_stock_threshold=min_stock_threshold,
                inventory_items=len(inventory),
                low_stock_count=len(low_stock_entries),
                should_refresh_menu=should_refresh,
                should_consider_purchase=should_purchase,
                low_stock_items=low_stock_items,
                procurement_suggestions=procurement_suggestions,
                sales_boost_suggestions=sales_boost_suggestions,
                wine_fair_watchlist=wine_fair_watchlist,
                menu_export=menu_export,
                menu_analysis=menu_analysis,
            )
            cls._latest_report = report

        await event_bus.publish(
            AgentEvent(
                source="wine_card_trigger",
                type="menu_updated",
                message=json.dumps(
                    {
                        "reason": reason.value,
                        "low_stock_count": report.low_stock_count,
                        "season": season.value,
                        "vat_country": vat_country.value,
                    }
                ),
            )
        )

        return report

    @staticmethod
    def _build_procurement_suggestions(
        low_stock_items: list[str],
        missing_categories: list[str],
    ) -> list[str]:
        suggestions: list[str] = []
        if low_stock_items:
            suggestions.append(
                "Replenish low-stock wines first, prioritizing top-selling labels and core by-the-glass items."
            )
        for category in missing_categories:
            suggestions.append(
                f"Add at least 2-4 references in missing category '{category}' to rebalance the list."
            )
        if not suggestions:
            suggestions.append(
                "No urgent procurement need detected; maintain current purchasing cadence and monitor weekly."
            )
        return suggestions[:8]

    @staticmethod
    def _build_sales_boost_suggestions(menu_analysis) -> list[str]:
        if not menu_analysis:
            return ["Run menu analysis first to generate sales boost suggestions."]
        suggestions = []
        if menu_analysis.by_the_glass_suggestions:
            suggestions.append(
                "Promote 3-6 by-the-glass items with staff pairing scripts to increase rotation."
            )
        if "sparkling" in menu_analysis.missing_categories:
            suggestions.append(
                "Add one entry-level sparkling by the glass to improve aperitif conversion."
            )
        suggestions.append(
            "Review weekly sell-through by section and rotate one low performer with a stronger alternative."
        )
        return suggestions[:8]

    @staticmethod
    def _build_wine_fair_watchlist(menu_analysis) -> list[str]:
        """Placeholder watchlist to connect with future external market feeds."""
        base_watchlist = [
            "ProWein (DE): track producer launches in weak sections.",
            "Wine Paris (FR): watch for balanced price/quality by-the-glass candidates.",
            "Vinitaly (IT): monitor trend varietals for underrepresented categories.",
        ]
        if not menu_analysis:
            return base_watchlist
        if menu_analysis.missing_categories:
            return base_watchlist + [
                f"Prioritize fair scouting for missing sections: {', '.join(menu_analysis.missing_categories)}."
            ]
        return base_watchlist

    @staticmethod
    async def run_event_listener():
        queue = event_bus.subscribe()
        try:
            while True:
                event: AgentEvent = await queue.get()
                if event.type != "wine_sold":
                    continue
                await WineCardTriggerService.run_once(
                    reason=TriggerReason.WINE_SOLD,
                    season=Season.WINTER,
                    vat_country=VatCountry.LU,
                    min_stock_threshold=2,
                )
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(queue)
