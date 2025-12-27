"""
Event registry for macro events.

Tracks scheduled and past events that impact commodity markets.
"""

from datetime import date
from typing import Dict, List, Optional
from .models import Event, EventType

# Event registry: maps event_id to Event
EVENT_REGISTRY: Dict[str, Event] = {}

def register_event(event: Event):
    """Register an event in the registry."""
    EVENT_REGISTRY[event.event_id] = event

def get_event(event_id: str) -> Optional[Event]:
    """Get an event by ID."""
    return EVENT_REGISTRY.get(event_id)

def get_all_events() -> List[Event]:
    """Get all registered events."""
    return list(EVENT_REGISTRY.values())

def get_events_by_date(event_date: date) -> List[Event]:
    """Get events on a specific date."""
    return [e for e in EVENT_REGISTRY.values() if e.event_date == event_date]

def get_upcoming_events(days_ahead: int = 7) -> List[Event]:
    """Get upcoming events within the next N days."""
    today = date.today()
    end_date = date.fromordinal(today.toordinal() + days_ahead)
    return [e for e in EVENT_REGISTRY.values() if today <= e.event_date <= end_date]

def get_events_by_type(event_type: EventType) -> List[Event]:
    """Get events of a specific type."""
    return [e for e in EVENT_REGISTRY.values() if e.event_type == event_type]

def get_events_for_market(market: str) -> List[Event]:
    """Get events that impact a specific market."""
    return [e for e in EVENT_REGISTRY.values() if market in e.impact_markets]

def link_event_to_signal(event_id: str, signal_id: str):
    """Link an event to a signal."""
    event = EVENT_REGISTRY.get(event_id)
    if event and signal_id not in event.related_signal_ids:
        event.related_signal_ids.append(signal_id)

