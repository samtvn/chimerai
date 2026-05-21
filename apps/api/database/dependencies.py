"""
Dependency injection helpers for database access.

Usage:
- For AI agents (read-only): from database.dependencies import get_read_only_db
- For write operations: from database.dependencies import get_db
"""

from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import AsyncSessionLocal, AsyncReadSessionLocal
from database.repositories.user_repository import UserRepository


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


_DEMO_USER_ID: UUID | None = None


async def get_demo_user_id(db: AsyncSession) -> UUID:
    global _DEMO_USER_ID
    if _DEMO_USER_ID:
        return _DEMO_USER_ID
    repo = UserRepository(db, read_only=True)
    user = await repo.get_by_username("chimerai_bistro")
    if not user:
        raise HTTPException(404, "Demo user not found")
    _DEMO_USER_ID = user.id
    return _DEMO_USER_ID
