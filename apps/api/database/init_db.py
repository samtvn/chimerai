"""
Run this script once to create all tables and seed the database.
Usage: uv run -m apps.api.database.init_db
"""

import asyncio

from sqlmodel import SQLModel

# Import all models so SQLModel registers them before create_all
import apps.api.database.models  # noqa: F401

from .database import engine
from .seeds.cellar import seed_cellars
from .seeds.transactions import seed_transactions
from .seeds.users import seed_users
from .seeds.wines import seed_wines
from .seeds.transactions_2 import seed_transactions_2


async def init_db(scenario: str = "default"):
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Tables created.")

    await seed_wines()
    await seed_users()
    match scenario:
        case "default":
            await seed_transactions()
        case "no_rose":
            await seed_transactions_2()

    await seed_cellars()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(init_db())
