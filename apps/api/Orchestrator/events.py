from pydantic import BaseModel, Field
from typing import Literal, Union, List
from datetime import datetime, UTC

class WineSoldEvent(BaseModel):
    event_type: Literal["wine_sold"] = "wine_sold"
    wine_ids: List[str]
    quantity: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class WineAddedEvent(BaseModel):
    event_type: Literal["wine_added"] = "wine_added"
    wine_ids: List[str]
    quantity: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class AnalysisRunEvent(BaseModel):
    event_type: Literal["analysis_run"] = "analysis_run"
    agent_name: str
    analysis_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

Event = Union[WineSoldEvent, WineAddedEvent, AnalysisRunEvent]
