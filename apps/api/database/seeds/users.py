from ..database import AsyncSessionLocal
from ..models.users import User
from sqlalchemy import select
from uuid6 import uuid7


async def seed_users():
    async with AsyncSessionLocal() as session:
        # Skip if already seeded
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Users already seeded, skipping.")
            return

        users = [
            User(
                id = uuid7(),
                firstname="John",
                lastname="Doe",
                username="chimerai_bistro",
                email="demo@chimerai.com",
                user_type="business",
                business_name="Chimerai Bistro",
            )
        ]

        session.add_all(users)
        await session.commit()
        print(f"Seeded {len(users)} users.")
