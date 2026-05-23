"""FastAPI routes for wine-card inventory, pricing, export, and analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.dependencies import get_demo_user_id, get_read_db
from .models import (
    MenuAnalysisResult,
    MenuExportResult,
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


@router.get("/inventory")
async def read_inventory(db: AsyncSession = Depends(get_read_db)):
    try:
        user_id = await get_demo_user_id(db)
        service = WineCardService(WineCardRepository(db))
        inventory = await service.read_inventory(user_id=user_id)
        return {"items": [item.model_dump() for item in inventory], "total": len(inventory)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read inventory: {exc}") from exc


@router.post("/pricing/preview", response_model=PricingResult)
async def preview_pricing(body: PricingPreviewInput):
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
    try:
        user_id = await get_demo_user_id(db)
        service = WineCardService(WineCardRepository(db))
        return await service.export_editable_menu(
            user_id=user_id,
            season=season,
            vat_country=vat_country,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export menu: {exc}") from exc


@router.get("/menu/analysis", response_model=MenuAnalysisResult)
async def analyze_wine_menu(
    season: Season = Season.WINTER,
    vat_country: VatCountry = VatCountry.LU,
    db: AsyncSession = Depends(get_read_db),
):
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


@router.post("/trigger/run", response_model=WineCardTriggerReport)
async def run_wine_card_trigger(
    reason: TriggerReason = TriggerReason.MANUAL,
    season: Season = Season.WINTER,
    vat_country: VatCountry = VatCountry.LU,
    min_stock_threshold: int = 2,
):
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
    return WineCardTriggerService.get_latest_report()
