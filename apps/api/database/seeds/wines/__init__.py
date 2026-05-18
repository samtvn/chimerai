from .dessert import seed_dessert
from .fortified import seed_fortified
from .red import seed_red
from .rose import seed_rose
from .sparkling import seed_sparkling
from .white import seed_white

__all__ = [
    "seed_dessert",
    "seed_fortified",
    "seed_red",
    "seed_rose",
    "seed_sparkling",
    "seed_white",
]

async def seed_wines():
    await seed_rose()
    await seed_fortified()
    await seed_sparkling()
    await seed_white()
    await seed_red()
    await seed_dessert()