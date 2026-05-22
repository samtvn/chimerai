from sqlalchemy import select
from ...database import AsyncSessionLocal
from ...models.wines import Wine


async def seed_sparkling():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(Wine).where(Wine.color == "sparkling").limit(1))
        if result.scalar_one_or_none():
            print("Sparkling wines already seeded, skipping.")
            return
        sparkling_wines = [
            Wine(
                id=672,
                producer="Pierre Moncuit",
                name="Blanc de Blancs Brut",
                region="Champagne",
                country="France",
                appellation="Champagne",
                vintage=None,
                grape_variety="Chardonnay",
                color="sparkling",
                alcohol=12.00,
                drink_from=2023,
                drink_to=2028,
                market_price=28.00,
                created_at="2026-05-18 11:41:15.096071",
            ),
            Wine(
                id=673,
                producer="Charles Heidsieck",
                name="Brut Réserve",
                region="Champagne",
                country="France",
                appellation="Champagne",
                vintage=None,
                grape_variety="Pinot Noir Chardonnay",
                color="sparkling",
                alcohol=12.00,
                drink_from=2023,
                drink_to=2030,
                market_price=34.00,
                created_at="2026-05-18 11:41:15.096071",
            ),
            Wine(
                id=674,
                producer="Billecart-Salmon",
                name="Brut Réserve",
                region="Champagne",
                country="France",
                appellation="Champagne",
                vintage=None,
                grape_variety="Champagne Blend",
                color="sparkling",
                alcohol=12.00,
                drink_from=2023,
                drink_to=2030,
                market_price=42.00,
                created_at="2026-05-18 11:41:15.096071",
            ),
            Wine(
                id=675,
                producer="Ruinart",
                name="Blanc de Blancs",
                region="Champagne",
                country="France",
                appellation="Champagne",
                vintage=None,
                grape_variety="Chardonnay",
                color="sparkling",
                alcohol=12.50,
                drink_from=2023,
                drink_to=2032,
                market_price=58.00,
                created_at="2026-05-18 11:41:15.096071",
            ),
            Wine(
                id=676,
                producer="Bollinger",
                name="Special Cuvée",
                region="Champagne",
                country="France",
                appellation="Champagne",
                vintage=None,
                grape_variety="Pinot Noir Blend",
                color="sparkling",
                alcohol=12.00,
                drink_from=2023,
                drink_to=2032,
                market_price=46.00,
                created_at="2026-05-18 11:41:15.096071",
            ),
        ]
        session.add_all(sparkling_wines)
        await session.commit()
        print(f"Seeded {len(sparkling_wines)} wines.")
