"""Structured models for wine-card inventory, pricing, menu export, and analysis."""

from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class VatCountry(str, Enum):
    LU = "LU"
    FR = "FR"
    BE = "BE"
    DE = "DE"


class TriggerReason(str, Enum):
    MANUAL = "manual"
    WINE_SOLD = "wine_sold"
    LOW_STOCK_SCAN = "low_stock_scan"


class Occasion(str, Enum):
    CHRISTMAS = "christmas"
    VALENTINE = "valentine"
    EASTER = "easter"
    BANQUET = "banquet"


class InventoryItem(BaseModel):
    wine_id: int
    producer: str
    wine_name: str
    region: str | None = None
    country: str | None = None
    appellation: str | None = None
    wine_color: str | None = None
    vintage: str | None = None
    grape_variety: str | None = None
    drink_from: int | None = None
    drink_to: int | None = None
    quantity: int = Field(ge=0)
    purchase_price_ht: float = Field(ge=0)
    avg_market_price: float | None = Field(default=None, ge=0)


class PricingResult(BaseModel):
    purchase_price_ht: float = Field(ge=0)
    vat_country: VatCountry
    markup_coefficient: float = Field(gt=0)
    vat_rate: float = Field(ge=0)
    selling_price_ht: float = Field(ge=0)
    selling_price_ttc: float = Field(ge=0)
    glass_price_ttc: float = Field(ge=0)


class MenuItem(BaseModel):
    section: str
    display_mode: Literal["glass", "bottle", "both"] = "both"
    vat_country: VatCountry
    vat_rate: float = Field(ge=0)
    wine_id: int
    producer: str
    wine_name: str
    vintage: str | None = None
    region: str | None = None
    appellation: str | None = None
    country: str | None = None
    quantity: int = Field(ge=0)
    purchase_price_ht: float = Field(ge=0)
    avg_market_price: float | None = Field(default=None, ge=0)
    selling_price_ttc: float = Field(ge=0)
    glass_price_ttc: float = Field(ge=0)


class MenuExportResult(BaseModel):
    season: Season
    vat_country: VatCountry
    items_count: int = Field(ge=0)
    markdown: str
    menu_items: list[MenuItem]


class SeasonalStrategy(BaseModel):
    focus: list[str]
    avoid: list[str]
    notes: str


class MenuAnalysisResult(BaseModel):
    season: Season
    strategy: SeasonalStrategy
    summary: str
    selected_for_menu: int = Field(ge=0)
    total_inventory_candidates: int = Field(ge=0)
    missing_categories: list[str]
    low_stock_warnings: list[str]
    cheap_wine_low_stock_alerts: list[str]
    duplicate_vintage_alerts: list[str]
    reprint_menu_recommended: bool
    by_the_glass_suggestions: list[str]
    section_counts: dict[str, int]


class WineCardTriggerReport(BaseModel):
    trigger_reason: TriggerReason
    triggered_at: datetime
    season: Season
    vat_country: VatCountry
    min_stock_threshold: int = Field(ge=1)
    inventory_items: int = Field(ge=0)
    low_stock_count: int = Field(ge=0)
    should_refresh_menu: bool
    should_consider_purchase: bool
    low_stock_items: list[str]
    procurement_suggestions: list[str]
    sales_boost_suggestions: list[str]
    wine_fair_watchlist: list[str]
    menu_export: MenuExportResult | None = None
    menu_analysis: MenuAnalysisResult | None = None


class OneShotMenuResult(BaseModel):
    occasion: Occasion
    season: Season
    vat_country: VatCountry
    by_glass_mode: bool
    service_count: int = Field(ge=3, le=5)
    menu_total_price_ttc: float | None = Field(default=None, ge=0)
    suggested_pairing_price_ttc: float | None = Field(default=None, ge=0)
    suggested_per_service_price_ttc: float | None = Field(default=None, ge=0)
    inventory_candidates: int = Field(ge=0)
    selected_items: int = Field(ge=0)
    summary: str
    llm_prompt: str
    pairing_notes: list[str]
    menu_export: MenuExportResult
    menu_analysis: MenuAnalysisResult
