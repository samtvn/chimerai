from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from ..models.transactions import Transaction, TransactionType
from .base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    def __init__(self, session: AsyncSession, read_only: bool = False):
        """Initialize TransactionRepository.

        Args:
            session: AsyncSession instance
            read_only: If True, only read operations are allowed
        """
        super().__init__(session, read_only)

    async def get_by_user_id(self, user_id: UUID, limit: int = 100) -> List[Transaction]:
        """Get all transactions for a user"""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_type(
        self, transaction_type: TransactionType, limit: int = 100
    ) -> List[Transaction]:
        """Get transactions by type (PURCHASE or SALE)"""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.type == transaction_type)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_purchases(self, user_id: UUID, limit: int = 100) -> List[Transaction]:
        """Get all purchases for a user"""
        result = await self.session.execute(
            select(Transaction)
            .where(
                and_(Transaction.user_id == user_id, Transaction.type == TransactionType.PURCHASE)
            )
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_sales(self, user_id: UUID, limit: int = 100) -> List[Transaction]:
        """Get all sales for a user"""
        result = await self.session.execute(
            select(Transaction)
            .where(and_(Transaction.user_id == user_id, Transaction.type == TransactionType.SALE))
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        return result.scalars().all()
