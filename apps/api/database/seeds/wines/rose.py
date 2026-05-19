from sqlalchemy import select
from ...database import AsyncSessionLocal
from ...models.wines import Wine


async def seed_rose():
     async with AsyncSessionLocal() as session:
         # Skip if already seeded
         result = await session.execute(select(Wine).where(Wine.color == "rose").limit(1))
         if result.scalar_one_or_none():
             print("Rosé wines already seeded, skipping.")
             return
         rose_wines = [
             Wine(
                 id=679,
                 producer="Château Minuty",
                 name="Prestige Rosé",
                 region="Provence",
                 country="France",
                 appellation="Côtes de Provence",
                 vintage=2023,
                 grape_variety="Grenache Cinsault Syrah",
                 color="rose",
                 alcohol=13.00,
                 drink_from=2023,
                 drink_to=2026,
                 market_price=14.00,
             ),
             Wine(
                 id=680,
                 producer="Domaines Ott",
                 name="By Ott Rosé",
                 region="Provence",
                 country="France",
                 appellation="Côtes de Provence",
                 vintage=2023,
                 grape_variety="Grenache Blend",
                 color="rose",
                 alcohol=13.00,
                 drink_from=2023,
                 drink_to=2026,
                 market_price=18.00,
             ),
             Wine(
                 id=681,
                 producer="Château d'Esclans",
                 name="Whispering Angel",
                 region="Provence",
                 country="France",
                 appellation="Côtes de Provence",
                 vintage=2023,
                 grape_variety="Grenache Blend",
                 color="rose",
                 alcohol=13.00,
                 drink_from=2023,
                 drink_to=2026,
                 market_price=19.00,
             ),
             Wine(
                 id=682,
                 producer="Clos Mireille",
                 name="Rosé",
                 region="Provence",
                 country="France",
                 appellation="Côtes de Provence",
                 vintage=2022,
                 grape_variety="Grenache Blend",
                 color="rose",
                 alcohol=13.00,
                 drink_from=2023,
                 drink_to=2027,
                 market_price=26.00,
             ),
             Wine(
                 id=683,
                 producer="Château Sainte Marguerite",
                 name="Fantastique Rosé",
                 region="Provence",
                 country="France",
                 appellation="Côtes de Provence",
                 vintage=2023,
                 grape_variety="Grenache Blend",
                 color="rose",
                 alcohol=13.00,
                 drink_from=2023,
                 drink_to=2026,
                 market_price=22.00,
             )
         ]
         session.add_all(rose_wines)
         await session.commit()
         print(f"Seeded {len(rose_wines)} wines.")