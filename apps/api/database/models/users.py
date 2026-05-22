from enum import Enum
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel
from uuid6 import uuid7

from .recommendations import Recommendation

if TYPE_CHECKING:
    from .cellar import Cellar
    from .recommendations import Recommendation
    from .transactions import Transaction


class UserType(str, Enum):
    BUSINESS = "business"
    INDIVIDUAL = "individual"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid7, primary_key=True, index=True)
    firstname: str
    lastname: str
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    user_type: UserType
    business_name: str | None = None

    cellars: List["Cellar"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")
    recommendations: List["Recommendation"] = Relationship(back_populates="user")
