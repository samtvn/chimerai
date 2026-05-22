from sqlalchemy import select
from uuid6 import uuid7
from datetime import datetime, timezone, timedelta
from ..database import AsyncSessionLocal
from ..models.transactions import Transaction, TransactionType
from ..models.users import User
from ..models.wines import Wine


async def seed_transactions():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(Transaction).limit(1))
        if result.scalar_one_or_none():
            print("Transactions already seeded, skipping.")
            return

        # Get the demo user
        user_result = await session.execute(select(User).where(User.username == "chimerai_bistro"))
        user = user_result.scalar_one_or_none()
        if not user:
            print("Demo user not found, skipping transaction seeding.")
            return

        # Get some wines to create transactions with
        wines_result = await session.execute(select(Wine).limit(10))
        wines = wines_result.scalars().all()
        if not wines:
            print("No wines found, skipping transaction seeding.")
            return

        transactions = []
        base_date = datetime.now(timezone.utc) - timedelta(days=30)

        # First, create PURCHASE transactions for the first 6 wines
        for idx in range(min(6, len(wines))):
            wine = wines[idx]
            quantity = 2 + (idx % 3)  # 2-4 bottles per purchase

            transactions.append(
                Transaction(
                    id=uuid7(),
                    wine_id=wine.id,
                    user_id=user.id,
                    quantity=quantity,
                    purchase_price=wine.market_price,
                    type=TransactionType.PURCHASE,
                    transaction_date=base_date + timedelta(days=idx),
                )
            )

        # Then, create SALE transactions for some of the purchased wines (FIFO will apply)
        for idx in range(min(4, len(wines))):
            wine = wines[idx]
            quantity = 1 + (idx % 2)  # 1-2 bottles per sale

            transactions.append(
                Transaction(
                    id=uuid7(),
                    wine_id=wine.id,
                    user_id=user.id,
                    quantity=quantity,
                    purchase_price=None,
                    type=TransactionType.SALE,
                    transaction_date=base_date + timedelta(days=7 + idx),
                )
            )

        session.add_all(transactions)
        await session.commit()
        print(f"Seeded {len(transactions)} transactions.")
