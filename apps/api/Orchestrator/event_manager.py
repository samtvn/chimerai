from collections import deque
from typing import List, Optional
from .events import Event

class EventManager:
    """
    Manages a deque of events in memory.
    """
    def __init__(self, max_events: int = 100):
        self.events = deque(maxlen=max_events)

    def add_event(self, event: Event):
        """Adds an event to the event queue."""
        self.events.append(event)

    def get_events(self) -> List[Event]:
        """Returns a list of all current events."""
        return list(self.events)

    def get_last_event(self) -> Optional[Event]:
        """Returns the most recent event."""
        if self.events:
            return self.events[-1]
        return None

# Singleton instance of the EventManager
event_manager = EventManager()
