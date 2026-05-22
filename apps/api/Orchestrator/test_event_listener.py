import asyncio
from contextlib import suppress
from uuid import UUID

from agents.event_bus import event_bus, AgentEvent
from Orchestrator.service import OrchestratorService
import Orchestrator.service as orchestrator_service


def test_event_listener_triggers_orchestrator(monkeypatch):
    async def run_case():
        triggered = asyncio.Event()
        captured: dict[str, object] = {}

        class DummyOrchestrator:
            def __init__(self, cellar_repo, user_id=None):
                captured["user_id"] = user_id

            async def run(self, trigger_event=None):
                captured["trigger_event"] = trigger_event
                triggered.set()
                return {}

        class DummyRepository:
            def __init__(self, session, read_only=False):
                captured["read_only"] = read_only
                captured["session"] = session

        class DummySession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_get_demo_user_id(session):
            return UUID("00000000-0000-0000-0000-000000000001")

        monkeypatch.setattr(orchestrator_service, "AsyncReadSessionLocal", lambda: DummySession())
        monkeypatch.setattr(orchestrator_service, "get_demo_user_id", fake_get_demo_user_id)
        monkeypatch.setattr(orchestrator_service, "CellarRepository", DummyRepository)
        monkeypatch.setattr(orchestrator_service, "CellarOrchestrator", DummyOrchestrator)

        task = asyncio.create_task(OrchestratorService.run_event_listener())

        for _ in range(50):
            if event_bus.subscriber_count:
                break
            await asyncio.sleep(0)

        await event_bus.publish(AgentEvent(source="test", type="wine_sold", message="{}"))

        await asyncio.wait_for(triggered.wait(), timeout=1)

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        assert captured["trigger_event"] == "wine_sold"

    asyncio.run(run_case())
