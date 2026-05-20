from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .cellar import Cellar
    from .users import User
    from .wines import Wine

class TransactionType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True
    )
    wine_id: int = Field(foreign_key="wines.id")
    user_id: UUID = Field(foreign_key="users.id")
    quantity: int
    purchase_price: Optional[float] = None
    type: TransactionType
    transaction_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: "User" = Relationship(back_populates="transactions")
    wine: "Wine" = Relationship(back_populates="transactions")
    cellars: List["Cellar"] = Relationship(back_populates="transaction")
