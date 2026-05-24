from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel
from uuid6 import uuid7

if TYPE_CHECKING:
    from .users import User


class RunSessionStatus(str, Enum):
    """Status of an agent run session."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunSession(SQLModel, table=True):
    """
    Tracks orchestrator run sessions for checkpoint resumability.
    
    Stores the thread_id and status per user, allowing the orchestrator
    to resume from the last checkpoint on subsequent triggers.
    """
    __tablename__ = "agent_run_sessions"
    
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    thread_id: str = Field(index=True)  # LangGraph thread ID for checkpoint recovery
    status: RunSessionStatus = Field(default=RunSessionStatus.RUNNING)
    trigger: str = ""  # The trigger message that started this session
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user: "User" = Relationship(back_populates="agent_run_sessions")
