from typing import TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum

if TYPE_CHECKING:
    from .transactions import Transaction
    from .users import User
    from .wines import Wine


class BottleStatus(str, Enum):
    IN_CELLAR = "in_cellar"
    SOLD = "sold"
    OPEN = "open"


class Cellar(SQLModel, table=True):
    __tablename__ = "cellar"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    wine_id: int = Field(foreign_key="wines.id")
    transaction_id: UUID = Field(foreign_key="transactions.id")
    status: BottleStatus = Field(default=BottleStatus.IN_CELLAR)

    user: "User" = Relationship(back_populates="cellars")
    wine: "Wine" = Relationship(back_populates="cellars")
    transaction: "Transaction" = Relationship(back_populates="cellars")
