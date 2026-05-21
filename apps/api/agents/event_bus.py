import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass
class AgentEvent:
    source: str
    type: str
    message: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return asdict(self)

    def to_sse(self):
        return json.dumps(self.to_dict())


class EventBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._latest_events: list[AgentEvent] = []
        self._max_history = 100

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event: AgentEvent):
        self._latest_events.append(event)
        if len(self._latest_events) > self._max_history:
            self._latest_events = self._latest_events[-self._max_history :]
        dead = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self._subscribers.remove(q)

    def get_history(self, limit: int = 50) -> list[AgentEvent]:
        return self._latest_events[-limit:]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


event_bus = EventBus()
