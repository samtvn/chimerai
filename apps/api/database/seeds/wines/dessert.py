from sqlalchemy import select
from ...database import AsyncSessionLocal
from ...models.wines import Wine


async def seed_dessert():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(Wine).where(Wine.color == "dessert").limit(1))
        if result.scalar_one_or_none():
            print("Dessert wines already seeded, skipping.")
            return
        dessert_wines = [
            Wine(
                id=671,
                producer="Château d'Yquem",
                name="Grand Vin",
                region="Bordeaux",
                country="France",
                appellation="Sauternes",
                vintage=2015,
                grape_variety="Sémillon Sauvignon Blanc",
                color="dessert",
                alcohol=14.00,
                drink_from=2025,
                drink_to=2070,
                market_price=220.00,
            )
        ]
        session.add_all(dessert_wines)
        await session.commit()
        print(f"Seeded {len(dessert_wines)} wines.")
