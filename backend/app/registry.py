"""
Simple internal signal registry.

Tracks all available signals with their stable identifiers, versions, and metadata.
This prepares the system for real data ingestion while still using mocked data.
"""

from typing import Dict, List
from datetime import date, timedelta
from .models import Signal, Direction, Confidence

# Signal registry: maps signal_id to signal metadata
SIGNAL_REGISTRY: Dict[str, Dict] = {
    "wti-rsi-technical": {
        "signal_id": "wti-rsi-technical",
        "version": "v1",
        "market": "WTI Crude Oil",
        "category": "Technical",
        "name": "RSI",
    },
    "gold-usd-trend-macro": {
        "signal_id": "gold-usd-trend-macro",
        "version": "v1",
        "market": "Gold",
        "category": "Macro",
        "name": "USD Trend",
    },
    "wti-inventories-fundamental": {
        "signal_id": "wti-inventories-fundamental",
        "version": "v1",
        "market": "WTI Crude Oil",
        "category": "Fundamental",
        "name": "Crude Inventories",
    },
    "copper-cot-sentiment": {
        "signal_id": "copper-cot-sentiment",
        "version": "v1",
        "market": "Copper",
        "category": "Sentiment",
        "name": "COT Positioning",
    },
    "brent-ma-crossover-technical": {
        "signal_id": "brent-ma-crossover-technical",
        "version": "v1",
        "market": "Brent Crude",
        "category": "Technical",
        "name": "Moving Average Crossover",
    },
}

def get_registry() -> Dict[str, Dict]:
    """Get the signal registry."""
    return SIGNAL_REGISTRY

def get_signal_by_id(signal_id: str) -> Dict:
    """Get signal metadata by ID."""
    return SIGNAL_REGISTRY.get(signal_id)

def list_all_signal_ids() -> List[str]:
    """List all registered signal IDs."""
    return list(SIGNAL_REGISTRY.keys())

