import pytest
from .event_manager import EventManager, event_manager
from .events import WineSoldEvent, WineAddedEvent, AnalysisRunEvent
import uuid


@pytest.fixture(autouse=True)
def clear_events():
    """Clears events from the manager before each test."""
    event_manager.events.clear()


def test_add_wine_sold_event():
    """Tests adding a WineSoldEvent."""
    event = WineSoldEvent(wine_ids=["wine-1", "wine-2"], quantity=2)
    event_manager.add_event(event)
    events = event_manager.get_events()
    assert len(events) == 1
    assert isinstance(events[0], WineSoldEvent)
    assert events[0].wine_ids == ["wine-1", "wine-2"]


def test_add_wine_added_event():
    """Tests adding a WineAddedEvent."""
    event = WineAddedEvent(wine_ids=["wine-3"], quantity=12)
    event_manager.add_event(event)
    events = event_manager.get_events()
    assert len(events) == 1
    assert isinstance(events[0], WineAddedEvent)
    assert events[0].quantity == 12


def test_add_analysis_run_event():
    """Tests adding an AnalysisRunEvent."""
    analysis_id = str(uuid.uuid4())
    event = AnalysisRunEvent(agent_name="TestAgent", analysis_id=analysis_id)
    event_manager.add_event(event)
    events = event_manager.get_events()
    assert len(events) == 1
    assert isinstance(events[0], AnalysisRunEvent)
    assert events[0].agent_name == "TestAgent"


def test_get_last_event():
    """Tests retrieving the most recent event."""
    event1 = WineSoldEvent(wine_ids=["wine-1"], quantity=1)
    event2 = WineAddedEvent(wine_ids=["wine-2"], quantity=5)
    event_manager.add_event(event1)
    event_manager.add_event(event2)
    last_event = event_manager.get_last_event()
    assert last_event == event2


def test_event_queue_max_length():
    """Tests that the event queue respects the maxlen property."""
    manager = EventManager(max_events=2)
    manager.add_event(WineSoldEvent(wine_ids=["1"], quantity=1))
    manager.add_event(WineSoldEvent(wine_ids=["2"], quantity=1))
    manager.add_event(WineSoldEvent(wine_ids=["3"], quantity=1))
    events = manager.get_events()
    assert len(events) == 2
    assert events[0].wine_ids == ["2"]  # The first event should have been pushed out
    assert events[1].wine_ids == ["3"]
