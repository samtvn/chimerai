from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""

    model: type[T]

    def __init__(self, session: AsyncSession, read_only: bool = False):
        self.session = session
        self.read_only = read_only

    def _check_write_allowed(self):
        """Raise error if trying to write in read-only mode"""
        if self.read_only:
            raise PermissionError(
                f"Cannot perform write operation in read-only mode. "
                f"Use get_db() instead of get_read_db() for write operations."
            )

    async def get_by_id(self, id) -> Optional[T]:
        """Get a single record by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination"""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        """Create a new record"""
        self._check_write_allowed()
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id, **kwargs) -> Optional[T]:
        """Update a record"""
        self._check_write_allowed()
        obj = await self.get_by_id(id)
        if not obj:
            return None

        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id) -> bool:
        """Delete a record"""
        self._check_write_allowed()
        obj = await self.get_by_id(id)
        if not obj:
            return False

        await self.session.delete(obj)
        await self.session.commit()
        return True
