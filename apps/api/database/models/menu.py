from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel
from uuid6 import uuid7

if TYPE_CHECKING:
    from .users import User
    from .wines import Wine


class MenuItem(SQLModel, table=True):
    __tablename__ = "menu_items"
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    wine_id: int = Field(foreign_key="wines.id")
    description: str = ""  # LLM-generated tasting note
    pairing_notes: str = ""  # LLM-generated food pairings
    position: int = 0  # order on the card
    is_active: bool = True  # shown on current menu?
    selling_price_ttc: float | None = None  # computed restaurant price TTC
    glass_price_ttc: float | None = None  # computed per-glass price TTC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: "User" = Relationship(back_populates="menu_items")
    wine: "Wine" = Relationship(back_populates="menu_items")
