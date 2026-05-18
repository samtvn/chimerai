from typing import TYPE_CHECKING
from uuid import UUID
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
    __tablename__ = "Cellar"

    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    wine_id: int = Field(foreign_key="wines.id", primary_key=True)
    transaction_id: UUID = Field(foreign_key="transactions.id", primary_key=True)
    status: BottleStatus = Field(default=BottleStatus.IN_CELLAR)

    user: "User" = Relationship(back_populates="cellars")
    wine: "Wine" = Relationship(back_populates="cellars")
    transaction: "Transaction" = Relationship(back_populates="cellars")
