"""Test script for WineCardAgent.

Run as module:
    python -m WineCardAgent.test

Or with pytest:
    pytest WineCardAgent/test.py
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from WineCardAgent.models import InventoryItem, Season, VatCountry
from WineCardAgent.pricing import (
    VAT_RATES_BY_COUNTRY,
    calculate_restaurant_price_ttc,
    get_vat_rate,
)
from WineCardAgent.service import WineCardService


def _sample_inventory() -> list[InventoryItem]:
    return [
        InventoryItem(
            wine_id=101,
            producer="Domaine Test",
            wine_name="Chablis Village",
            region="Burgundy",
            country="France",
            appellation="Chablis",
            wine_color="white",
            vintage="2022",
            grape_variety="Chardonnay",
            quantity=8,
            purchase_price_ht=12.5,
            avg_market_price=19.0,
        ),
        InventoryItem(
            wine_id=102,
            producer="Maison Rouge",
            wine_name="Cotes du Rhone",
            region="Rhone",
            country="France",
            appellation="Cotes du Rhone",
            wine_color="red",
            vintage="2021",
            grape_variety="Grenache Syrah",
            quantity=5,
            purchase_price_ht=9.8,
            avg_market_price=15.5,
        ),
        InventoryItem(
            wine_id=103,
            producer="Bubbles Lab",
            wine_name="Brut Reserve",
            region="Champagne",
            country="France",
            appellation="Champagne",
            wine_color="sparkling",
            vintage=None,
            grape_variety="Chardonnay Pinot Noir",
            quantity=2,
            purchase_price_ht=18.0,
            avg_market_price=29.0,
        ),
    ]


class _FakeWineCardRepository:
    def __init__(self, items: list[InventoryItem]):
        self.items = items

    async def read_inventory(self, user_id, limit: int = 1000) -> list[InventoryItem]:
        return self.items[:limit]


def test_imports():
    from WineCardAgent.routes import router  # noqa: F401
    from WineCardAgent.repository import WineCardRepository  # noqa: F401

    assert True


def test_pricing_math():
    result = calculate_restaurant_price_ttc(10.0)
    assert result.purchase_price_ht == 10.0
    assert result.vat_country == VatCountry.LU
    assert result.vat_rate == 0.17
    assert result.markup_coefficient > 0
    assert result.selling_price_ttc >= result.purchase_price_ht
    assert result.glass_price_ttc > 0


def test_vat_country_constants():
    assert VAT_RATES_BY_COUNTRY[VatCountry.LU] == 0.17
    assert VAT_RATES_BY_COUNTRY[VatCountry.FR] == 0.20
    assert VAT_RATES_BY_COUNTRY[VatCountry.BE] == 0.21
    assert VAT_RATES_BY_COUNTRY[VatCountry.DE] == 0.19

    assert get_vat_rate("LU") == 0.17
    assert get_vat_rate("fr") == 0.20


async def test_service_export_and_analysis_offline():
    service = WineCardService(_FakeWineCardRepository(_sample_inventory()))
    user_id = uuid4()

    inventory = await service.read_inventory(user_id)
    assert len(inventory) == 3

    menu = await service.export_editable_menu(user_id, Season.WINTER, vat_country=VatCountry.FR)
    assert menu.items_count == 3
    assert menu.vat_country == VatCountry.FR
    assert "Editable Wine List" in menu.markdown
    assert menu.menu_items[0].vat_country == VatCountry.FR
    assert menu.menu_items[0].vat_rate == 0.20

    analysis = await service.analyze_menu(user_id, Season.WINTER, vat_country=VatCountry.FR)
    assert analysis.season == Season.WINTER
    assert isinstance(analysis.section_counts, dict)
    assert len(analysis.by_the_glass_suggestions) <= 6


async def test_database_smoke_optional():
    """Optional DB smoke test. Enable with RUN_WINECARD_DB_TEST=1."""
    if os.getenv("RUN_WINECARD_DB_TEST") != "1":
        print("SKIP: Set RUN_WINECARD_DB_TEST=1 to run DB smoke test")
        return True

    from database.database import AsyncReadSessionLocal
    from database.dependencies import get_demo_user_id
    from WineCardAgent.repository import WineCardRepository

    async with AsyncReadSessionLocal() as session:
        user_id = await get_demo_user_id(session)
        service = WineCardService(WineCardRepository(session))
        inventory = await service.read_inventory(user_id)
        print(f"DB inventory rows: {len(inventory)}")
        return True


async def main():
    print("=" * 60)
    print("WineCardAgent - Test Suite")
    print("=" * 60)

    results: list[tuple[str, bool]] = []

    sync_tests = [
        ("Module Imports", test_imports),
        ("Pricing Math", test_pricing_math),
        ("VAT Country Constants", test_vat_country_constants),
    ]
    for name, fn in sync_tests:
        try:
            fn()
            print(f"PASS: {name}")
            results.append((name, True))
        except Exception as exc:
            print(f"FAIL: {name} -> {exc}")
            results.append((name, False))

    async_tests = [
        ("Offline Service Export + Analysis", test_service_export_and_analysis_offline),
        ("Database Smoke (Optional)", test_database_smoke_optional),
    ]
    for name, fn in async_tests:
        try:
            value = await fn()
            ok = True if value is None else bool(value)
            print(f"{'PASS' if ok else 'FAIL'}: {name}")
            results.append((name, ok))
        except Exception as exc:
            print(f"FAIL: {name} -> {exc}")
            results.append((name, False))

    print("-" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"Summary: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    raise SystemExit(0 if success else 1)
