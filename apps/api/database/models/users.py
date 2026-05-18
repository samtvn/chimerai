from typing import List, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cellar import Cellar
    from .transactions import Transaction

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True
    )
    firstname: str
    lastname: str

    cellars: List["Cellar"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")
