from sqlalchemy import select, and_
from ..database import AsyncSessionLocal
from ..models.cellar import Cellar, BottleStatus
from ..models.users import User
from ..models.transactions import Transaction, TransactionType


async def seed_cellars():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(Cellar).limit(1))
        if result.scalar_one_or_none():
            print("Cellars already seeded, skipping.")
            return

        # Get the demo user
        user_result = await session.execute(
            select(User).where(User.username == "chimerai_bistro")
        )
        user = user_result.scalar_one_or_none()
        if not user:
            print("Demo user not found, skipping cellar seeding.")
            return

        # Get transactions ordered by creation (PURCHASE first, then SALE)
        transactions_result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.id)  # Order by ID to ensure consistent FIFO
        )
        transactions = transactions_result.scalars().all()
        if not transactions:
            print("No transactions found, skipping cellar seeding.")
            return

        cellars_to_add = []
        
        # First pass: Create all bottles from PURCHASE transactions
        for transaction in transactions:
            if transaction.type == TransactionType.PURCHASE:
                for bottle_idx in range(transaction.quantity):
                    cellars_to_add.append(
                        Cellar(
                            user_id=user.id,
                            wine_id=transaction.wine_id,
                            transaction_id=transaction.id,
                            status=BottleStatus.IN_CELLAR,
                        )
                    )
        
        # Commit the purchase bottles first so they exist for FIFO matching
        session.add_all(cellars_to_add)
        await session.commit()
        
        # Second pass: Mark bottles as SOLD from SALE transactions (FIFO)
        for transaction in transactions:
            if transaction.type == TransactionType.SALE:
                # For sales, we need to find the oldest bottles of the same wine and mark them as SOLD
                # Get all IN_CELLAR bottles of this wine, ordered by creation (FIFO)
                oldest_bottles_result = await session.execute(
                    select(Cellar)
                    .where(
                        and_(
                            Cellar.user_id == user.id,
                            Cellar.wine_id == transaction.wine_id,
                            Cellar.status == BottleStatus.IN_CELLAR,
                        )
                    )
                    .order_by(Cellar.id)  # Oldest first (by UUID creation order)
                    .limit(transaction.quantity)
                )
                bottles_to_sell = oldest_bottles_result.scalars().all()
                
                # Mark them as SOLD
                for bottle in bottles_to_sell:
                    bottle.status = BottleStatus.SOLD
        
        await session.commit()
        print("Seeded cellar entries with FIFO sales logic.")
