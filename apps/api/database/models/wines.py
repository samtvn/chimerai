from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cellar import Cellar
    from .transactions import Transaction

# TODO: change vector number depending on the embedding model we will choose
class Wine(SQLModel, table=True):
    __tablename__ = "wines"

    id: int = Field(primary_key=True)
    name: str = Field(nullable=False)
    producer: str = Field(nullable=False)
    country: str
    region: str
    appellation: Optional[str] = None
    vintage: Optional[str] = None
    grape_variety: Optional[str] = None
    color: str
    alcohol: float
    drink_from: Optional[int] = None
    drink_to: Optional[int] = None
    market_price: Optional[float] = None

    cellars: List["Cellar"] = Relationship(back_populates="wine")
    transactions: List["Transaction"] = Relationship(back_populates="wine")
