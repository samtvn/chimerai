from enum import Enum
from typing import List, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .cellar import Cellar
    from .users import User
    from .wines import Wine


class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True
    )
    user_id: UUID = Field(foreign_key="users.id", index=True)
    wine_id: int = Field(foreign_key="wines.id", index=True)
    quantity: int
    market_price: float
    priority_score: float
    recommendation_reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


    user: "User" = Relationship()
    wine: "Wine" = Relationship()
