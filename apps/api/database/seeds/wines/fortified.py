from sqlalchemy import select
from ...database import AsyncSessionLocal
from ...models.wines import Wine


async def seed_fortified():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(Wine).where(Wine.color == "fortified").limit(1))
        if result.scalar_one_or_none():
            print("Fortified wines already seeded, skipping.")
            return
        fortified_wines = [
            Wine(
                id=667,
                producer="Taylor's",
                name="Late Bottled Vintage",
                region="Douro",
                country="Portugal",
                appellation="Port",
                vintage=2018,
                grape_variety="Touriga Nacional Blend",
                color="fortified",
                alcohol=20.00,
                drink_from=2023,
                drink_to=2045,
                market_price=18.00,
            ),
            Wine(
                id=668,
                producer="Niepoort",
                name="10 Years Old Tawny",
                region="Douro",
                country="Portugal",
                appellation="Port",
                vintage=None,
                grape_variety="Touriga Blend",
                color="fortified",
                alcohol=20.00,
                drink_from=2023,
                drink_to=2050,
                market_price=24.00,
            ),
            Wine(
                id=669,
                producer="Lustau",
                name="East India Solera",
                region="Jerez",
                country="Spain",
                appellation="Sherry",
                vintage=None,
                grape_variety="Palomino Pedro Ximénez",
                color="fortified",
                alcohol=20.00,
                drink_from=2023,
                drink_to=2050,
                market_price=14.00,
            ),
            Wine(
                id=670,
                producer="Equipo Navazos",
                name="La Bota Fino",
                region="Jerez",
                country="Spain",
                appellation="Sherry",
                vintage=None,
                grape_variety="Palomino",
                color="fortified",
                alcohol=15.00,
                drink_from=2023,
                drink_to=2040,
                market_price=28.00,
            ),
        ]
        session.add_all(fortified_wines)
        await session.commit()
        print(f"Seeded {len(fortified_wines)} wines.")
