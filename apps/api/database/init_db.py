"""
Run this script once to create all tables and seed the database.
Usage: uv run -m database.init_db
"""
import asyncio
from sqlmodel import SQLModel

# Import all models so SQLModel registers them before create_all
from database.models.users import User  # noqa: F401
from database.models.wines import Wine  # noqa: F401
from database.models.cellar import Cellar  # noqa: F401
from database.models.transactions import Transaction  # noqa: F401
from database.database import engine
from database.seeds.wines import seed_wines
from database.seeds.users import seed_users

async def init_db():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Tables created.")

    await seed_wines()
    await seed_users()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(init_db())
