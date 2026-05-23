"""Structured models for wine-card inventory, pricing, menu export, and analysis."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


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
    missing_categories: list[str]
    low_stock_warnings: list[str]
    by_the_glass_suggestions: list[str]
    section_counts: dict[str, int]
