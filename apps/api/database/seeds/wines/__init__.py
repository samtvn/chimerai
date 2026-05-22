import asyncio
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
    await asyncio.gather(
        seed_rose(),
        seed_fortified(),
        seed_sparkling(),
        seed_white(),
        seed_red(),
        seed_dessert(),
    )
