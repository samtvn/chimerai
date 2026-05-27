"""FastAPI routes for wine-card inventory, pricing, export, and analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.dependencies import get_demo_user_id, get_read_db
from apps.api.database.repositories.user_repository import UserRepository
from .models import (
    MenuAnalysisResult,
    MenuExportResult,
    Occasion,
    OneShotMenuResult,
    PricingResult,
    Season,
    TriggerReason,
    VatCountry,
    WineCardTriggerReport,
)
from .pricing import calculate_restaurant_price_ttc
from .repository import WineCardRepository
from .service import WineCardService
from .trigger_service import WineCardTriggerService

router = APIRouter(prefix="/api/wine-card", tags=["wine-card"])


class PricingPreviewInput(BaseModel):
    purchase_price_ht: float = Field(ge=0)
    vat_country: VatCountry = VatCountry.LU


class OneShotMenuInput(BaseModel):
    occasion: Occasion
    vat_country: VatCountry = VatCountry.LU
    service_count: int = Field(default=3, ge=3, le=5)
    menu_total_price_ttc: float | None = Field(default=None, ge=0)


async def _resolve_restaurant_name(db: AsyncSession, user_id) -> str:
    """Resolve display name used in exported menu headers.

    Args:
        db: Read-only async session.
        user_id: Restaurant user identifier.

    Returns:
        Business name if present, otherwise user full name, otherwise default.
    """
    user = await UserRepository(db, read_only=True).get_by_id(user_id)
    if not user:
        return "Chimerai Bistro"
    if user.business_name:
        return user.business_name
    fullname = f"{user.firstname} {user.lastname}".strip()
    return fullname or "Chimerai Bistro"


@router.get("/inventory")
async def read_inventory(db: AsyncSession = Depends(get_read_db)):
    """Return normalized inventory rows for Wine Card workflows.

    Args:
        db: Read-only async session dependency.

    Returns:
        Inventory payload with items and total count.
    """
    try:
        user_id = await get_demo_user_id(db)
        service = WineCardService(WineCardRepository(db))
        inventory = await service.read_inventory(user_id=user_id)
        return {"items": [item.model_dump() for item in inventory], "total": len(inventory)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read inventory: {exc}") from exc


@router.post("/pricing/preview", response_model=PricingResult)
async def preview_pricing(body: PricingPreviewInput):
    """Preview TTC pricing for a single purchase price input.

    Args:
        body: Price and VAT-country input.

    Returns:
        Computed pricing breakdown used by the UI pricing widget.
    """
    return calculate_restaurant_price_ttc(
        body.purchase_price_ht,
        vat_country=body.vat_country,
    )


@router.get("/menu/export", response_model=MenuExportResult)
async def export_editable_menu(
    season: Season = Season.WINTER,
    vat_country: VatCountry = VatCountry.LU,
    db: AsyncSession = Depends(get_read_db),
):
    """Generate seasonal editable menu export for the demo user.

    Args:
        season: Seasonal profile used for menu selection.
        vat_country: VAT-country context for TTC prices.
        db: Read-only async session dependency.

    Returns:
        Rendered menu export payload (markdown + structured menu items).
    """
    try:
        user_id = await get_demo_user_id(db)
        restaurant_name = await _resolve_restaurant_name(db, user_id)
        service = WineCardService(WineCardRepository(db))
        return await service.export_editable_menu(
            user_id=user_id,
            season=season,
            vat_country=vat_country,
            restaurant_name=restaurant_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export menu: {exc}") from exc


@router.get("/menu/analysis", response_model=MenuAnalysisResult)
async def analyze_wine_menu(
    season: Season = Season.WINTER,
    vat_country: VatCountry = VatCountry.LU,
    db: AsyncSession = Depends(get_read_db),
):
    """Run strategy analysis for the current seasonal menu candidate set.

    Args:
        season: Seasonal profile used for curation.
        vat_country: VAT-country context used by price-based suggestions.
        db: Read-only async session dependency.

    Returns:
        Menu analysis with gaps, warnings, and section-level diagnostics.
    """
    try:
        user_id = await get_demo_user_id(db)
        service = WineCardService(WineCardRepository(db))
        return await service.analyze_menu(
            user_id=user_id,
            season=season,
            vat_country=vat_country,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyze menu: {exc}") from exc


@router.post("/menu/one-shot", response_model=OneShotMenuResult)
async def generate_one_shot_menu(
    body: OneShotMenuInput,
    db: AsyncSession = Depends(get_read_db),
):
    """Generate one-shot event menu with export and strategy analysis.

    Args:
        body: Occasion, VAT and service-format input.
        db: Read-only async session dependency.

    Returns:
        One-shot menu result including export, analysis and pairing hints.
    """
    try:
        user_id = await get_demo_user_id(db)
        restaurant_name = await _resolve_restaurant_name(db, user_id)
        service = WineCardService(WineCardRepository(db))
        return await service.generate_one_shot_menu(
            user_id=user_id,
            occasion=body.occasion,
            vat_country=body.vat_country,
            service_count=body.service_count,
            menu_total_price_ttc=body.menu_total_price_ttc,
            restaurant_name=restaurant_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate one-shot menu: {exc}") from exc


@router.post("/trigger/run", response_model=WineCardTriggerReport)
async def run_wine_card_trigger(
    reason: TriggerReason = TriggerReason.MANUAL,
    season: Season = Season.WINTER,
    vat_country: VatCountry = VatCountry.LU,
    min_stock_threshold: int = 2,
):
    """Execute one Wine Strategy Check cycle on demand.

    Args:
        reason: Trigger reason shown in the strategy report.
        season: Seasonal context used by downstream menu refresh.
        vat_country: VAT-country context for generated prices.
        min_stock_threshold: Threshold used to classify low-stock entries.

    Returns:
        Trigger report used by the Wine Strategy Check UI section.
    """
    try:
        return await WineCardTriggerService.run_once(
            reason=reason,
            season=season,
            vat_country=vat_country,
            min_stock_threshold=min_stock_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run trigger: {exc}") from exc


@router.get("/trigger/latest", response_model=WineCardTriggerReport | None)
async def get_latest_wine_card_trigger_report():
    """Return the latest in-memory strategy trigger report.

    Returns:
        Latest trigger report, or ``None`` when no trigger has run yet.
    """
    return WineCardTriggerService.get_latest_report()
