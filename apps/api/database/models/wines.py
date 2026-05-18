from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Column, Field, Relationship, SQLModel
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from .cellar import Cellar
    from .transactions import Transaction
    from .users import User

# TODO: change vector number depending on the embedding model we will choose
class Wine(SQLModel, table=True):
    __tablename__ = "wines"

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True
    )
    name: str = Field(unique=True, nullable=False)
    producer: str = Field(unique=True, nullable=False)
    country: str
    region: str
    appelation: Optional[str] = None
    vintage: Optional[str] = None
    grape_variety: Optional[str] = None
    colour: str
    alcohol: float
    drink_from: Optional[int] = None
    drink_to: Optional[int] = None
    market_price: Optional[float] = None

    users: List["User"] = Relationship(back_populates="wines", link_model="Cellar")
    cellars: List["Cellar"] = Relationship(back_populates="wine")
    transactions: List["Transaction"] = Relationship(back_populates="wine")
