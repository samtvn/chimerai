import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from uuid6 import uuid7

from ..database import AsyncSessionLocal
from ..models.transactions import Transaction, TransactionType
from ..models.users import User
from ..models.wines import Wine


async def seed_transactions_3():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Transaction).limit(1))
        if result.scalar_one_or_none():
            print("Transactions already seeded, skipping.")
            return

        user_result = await session.execute(select(User).where(User.username == "chimerai_bistro"))
        user = user_result.scalar_one_or_none()
        if not user:
            print("Demo user not found, skipping transaction seeding.")
            return

        wines_result = await session.execute(select(Wine))
        wines = wines_result.scalars().all()
        if not wines:
            print("No wines found, skipping transaction seeding.")
            return

        transactions = []
        inventory: dict[int, int] = {}
        # Start from 200 days ago and work forward to today
        # This ensures all seeded transactions are in the past
        base_date = datetime.now(timezone.utc) - timedelta(days=200)

        target_transactions = 200
        target_cellar = 100
        current_cellar = 0
        day = 0
        tx_count = 0

        random.seed(42)

        while tx_count < target_transactions:
            wine = random.choice(wines)
            wine_id = wine.id
            available = inventory.get(wine_id, 0)
            date = base_date + timedelta(days=day, hours=random.randint(8, 20))

            if current_cellar <= target_cellar - 3 or available == 0:
                quantity = random.randint(2, 25)
                transactions.append(
                    Transaction(
                        id=uuid7(),
                        wine_id=wine_id,
                        user_id=user.id,
                        quantity=quantity,
                        price=wine.market_price + random.uniform(-5, 5),
                        type=TransactionType.PURCHASE,
                        transaction_date=date,
                    )
                )
                inventory[wine_id] = available + quantity
                current_cellar += quantity
                tx_count += 1
            elif current_cellar >= target_cellar + 10 and available >= 1:
                quantity = min(random.randint(1, 3), available)
                transactions.append(
                    Transaction(
                        id=uuid7(),
                        wine_id=wine_id,
                        user_id=user.id,
                        quantity=quantity,
                        price=wine.market_price + random.uniform(-5, 5),
                        type=TransactionType.SALE,
                        transaction_date=date,
                    )
                )
                inventory[wine_id] = available - quantity
                current_cellar -= quantity
                tx_count += 1
            elif available >= 1:
                if random.random() < 0.4 and current_cellar > target_cellar:
                    quantity = min(random.randint(1, 3), available)
                    transactions.append(
                        Transaction(
                            id=uuid7(),
                            wine_id=wine_id,
                            user_id=user.id,
                            quantity=quantity,
                            price=wine.market_price + random.uniform(-5, 5),
                            type=TransactionType.SALE,
                            transaction_date=date,
                        )
                    )
                    inventory[wine_id] = available - quantity
                    current_cellar -= quantity
                    tx_count += 1
                else:
                    quantity = random.randint(2, 10)
                    transactions.append(
                        Transaction(
                            id=uuid7(),
                            wine_id=wine_id,
                            user_id=user.id,
                            quantity=quantity,
                            price=wine.market_price,
                            type=TransactionType.PURCHASE,
                            transaction_date=date,
                        )
                    )
                    inventory[wine_id] = available + quantity
                    current_cellar += quantity
                    tx_count += 1
            else:
                quantity = random.randint(2, 10)
                transactions.append(
                    Transaction(
                        id=uuid7(),
                        wine_id=wine_id,
                        user_id=user.id,
                        quantity=quantity,
                        price=wine.market_price,
                        type=TransactionType.PURCHASE,
                        transaction_date=date,
                    )
                )
                inventory[wine_id] = available + quantity
                current_cellar += quantity
                tx_count += 1

            day += 1

        session.add_all(transactions)
        await session.commit()

        purchase_count = sum(1 for t in transactions if t.type == TransactionType.PURCHASE)
        sale_count = sum(1 for t in transactions if t.type == TransactionType.SALE)
        print(
            f"Seeded {len(transactions)} transactions ({purchase_count} purchases, {sale_count} sales)."
        )
        print(f"Net bottles in cellar: {current_cellar}")
