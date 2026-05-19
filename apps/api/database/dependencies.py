"""
Dependency injection helpers for database access.

Usage:
- For AI agents (read-only): from database.dependencies import get_read_only_db
- For write operations: from database.dependencies import get_db
"""

from sqlalchemy.ext.asyncio import AsyncSession
from database.database import AsyncSessionLocal, AsyncReadSessionLocal


async def get_db() -> AsyncSession:
    """Get a write-enabled database session.
    
    Use this for routes that create, update, or delete data.
    
    Example:
        @app.post("/users")
        async def create_user(db: AsyncSession = Depends(get_db)):
            repo = UserRepository(db, read_only=False)
            return await repo.create(name="John")
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_read_db() -> AsyncSession:
    """Get a read-only database session (replica).
    
    Use this for routes that only read data, especially for AI agents.
    This uses the read replica if configured, otherwise falls back to primary.
    
    Example:
        @app.get("/users/{username}")
        async def get_user(username: str, db: AsyncSession = Depends(get_read_db)):
            repo = UserRepository(db, read_only=True)
            return await repo.get_by_username(username)
    """
    async with AsyncReadSessionLocal() as session:
        yield session
