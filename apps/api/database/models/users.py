from typing import List
from uuid import UUID
from database.models.wines import UserWineLink, Wine
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid7, 
        primary_key=True,
        index=True
    )
    firstname: str
    lastname: str
    wines: List[Wine] = Relationship(back_populates="users", link_model=UserWineLink)