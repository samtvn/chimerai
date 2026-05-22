"""
Drops all tables in the public schema regardless of SQLModel metadata.
Usage: uv run -m apps.api.database.drop_db
"""

import asyncio
from sqlalchemy import text
from .database import engine


async def drop_db():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("Done. All tables dropped.")


if __name__ == "__main__":
    asyncio.run(drop_db())
