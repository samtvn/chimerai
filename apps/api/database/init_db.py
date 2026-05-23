"""
Run this script once to create all tables and seed the database.
Usage: uv run -m apps.api.database.init_db
"""

import asyncio

from sqlmodel import SQLModel

from .database import engine

# Import all models so SQLModel registers them before create_all
from .models.cellar import Cellar  # noqa: F401
from .models.menu import MenuItem  # noqa: F401
from .models.transactions import Transaction  # noqa: F401
from .models.users import User  # noqa: F401
from .models.wines import Wine  # noqa: F401
from .seeds.cellar import seed_cellars
from .seeds.transactions import seed_transactions
from .seeds.users import seed_users
from .seeds.wines import seed_wines


async def init_db():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Tables created.")

    await seed_wines()
    await seed_users()
    await seed_transactions()
    await seed_cellars()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(init_db())
