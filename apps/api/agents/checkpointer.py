import os

from fastapi.concurrency import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@asynccontextmanager
async def get_checkpointer():
    """
    Creates an AsyncPostgresSaver checkpointer using the app's DATABASE_URL.
    Used as an async context manager so the connection is properly closed.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    conn_string = db_url.replace("postgresql+psycopg://", "postgresql://")

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
