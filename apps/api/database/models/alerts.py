from typing import Optional, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .users import User


class AlertSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    message: str
    severity: AlertSeverity = Field(default=AlertSeverity.INFO)
    source_agent: Optional[str] = None
    read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: "User" = Relationship()
