from typing import List, Optional
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Column, Field, Relationship, SQLModel
from pgvector.sqlalchemy import Vector
from .users import User

class UserWineLink(SQLModel, table=True):
    __tablename__ = "users_wine"
    
    wine_id: UUID = Field(foreign_key="wines.lwin", primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)

# TODO: change vector number depending on the embedding model we will choose
class Wine(SQLModel, table=True):
    __tablename__ = "wines"

    lwin: UUID = Field(
        default_factory=uuid7, 
        primary_key=True
    )
    display_name: str = Field(unique=True, nullable=False)
    producer: str = Field(unique=True, nullable=False)
    wine: Optional[str] = Field(unique=True, default=None)
    country: str
    region: str
    sub_region: Optional[str] = None
    site: Optional[str] = None
    parcel: Optional[str] = None
    colour: str
    type: str
    sub_type: str
    designation: Optional[str] = None
    classification: Optional[str] = None
    taste: List[float] = Field(sa_column=Column(Vector(3))) 

    # Relationship back to users
    users: List["User"] = Relationship(back_populates="wines", link_model=UserWineLink)
