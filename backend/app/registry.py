"""
Simple internal signal registry.

Tracks all available signals with their stable identifiers, versions, and metadata.
This prepares the system for real data ingestion while still using mocked data.
"""

from typing import Dict, List

# Signal registry: maps signal_id to signal metadata
SIGNAL_REGISTRY: Dict[str, Dict] = {
    "wti-rsi-technical": {
        "signal_id": "wti-rsi-technical",
        "version": "v1",
        "market": "WTI Crude Oil",
        "category": "Technical",
        "name": "RSI",
        "validity_window": "daily",
        "signal_type": "tactical",
        "decay_behavior": "RSI signals typically remain valid for 1-3 days. Momentum can reverse quickly, so this signal should be monitored daily.",
        "related_signal_ids": ["brent-ma-crossover-technical"],
        "related_markets": ["Brent Crude"],
    },
    "gold-usd-trend-macro": {
        "signal_id": "gold-usd-trend-macro",
        "version": "v1",
        "market": "Gold",
        "category": "Macro",
        "name": "USD Trend",
        "validity_window": "weekly",
        "signal_type": "structural",
        "decay_behavior": "USD trends typically persist for weeks to months. This signal remains relevant until USD trend reverses or consolidates.",
        "related_signal_ids": [],
        "related_markets": ["Silver", "Platinum"],
    },
    "wti-inventories-fundamental": {
        "signal_id": "wti-inventories-fundamental",
        "version": "v1",
        "market": "WTI Crude Oil",
        "category": "Fundamental",
        "name": "Crude Inventories",
        "validity_window": "weekly",
        "signal_type": "structural",
        "decay_behavior": "Inventory data impacts prices for 1-2 weeks until next report. Signal relevance decreases as next report approaches.",
        "related_signal_ids": [],
        "related_markets": ["Brent Crude", "Heating Oil", "RBOB"],
    },
    "copper-cot-sentiment": {
        "signal_id": "copper-cot-sentiment",
        "version": "v1",
        "market": "Copper",
        "category": "Sentiment",
        "name": "COT Positioning",
        "validity_window": "weekly",
        "signal_type": "tactical",
        "decay_behavior": "COT positioning signals are most relevant for 1-2 weeks. Extreme positioning can persist longer, but moderate positioning changes more frequently.",
        "related_signal_ids": [],
        "related_markets": ["Aluminum", "Zinc"],
    },
    "brent-ma-crossover-technical": {
        "signal_id": "brent-ma-crossover-technical",
        "version": "v1",
        "market": "Brent Crude",
        "category": "Technical",
        "name": "Moving Average Crossover",
        "validity_window": "daily",
        "signal_type": "tactical",
        "decay_behavior": "MA crossovers can reverse quickly. Signal remains valid for 2-5 days typically, but should be confirmed with other indicators.",
        "related_signal_ids": ["wti-rsi-technical"],
        "related_markets": ["WTI Crude Oil"],
    },
}

# Market groupings
MARKET_GROUPS: Dict[str, List[str]] = {
    "energy": ["WTI Crude Oil", "Brent Crude", "Heating Oil", "RBOB", "Henry Hub Nat Gas"],
    "metals": ["Gold", "Silver", "Copper", "Platinum", "Aluminum", "Zinc"],
    "ags": ["Corn", "Soybeans", "Wheat"],
}

# Signal relationships: maps signal_id to list of related signal IDs with relationship type
SIGNAL_RELATIONSHIPS: Dict[str, List[Dict[str, str]]] = {
    "wti-rsi-technical": [
        {"signal_id": "brent-ma-crossover-technical", "relationship_type": "related"}
    ],
    "brent-ma-crossover-technical": [
        {"signal_id": "wti-rsi-technical", "relationship_type": "related"}
    ],
    "wti-inventories-fundamental": [
        {"signal_id": "wti-rsi-technical", "relationship_type": "confirms"}
    ],
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

def get_market_groups() -> Dict[str, List[str]]:
    """Get market groupings."""
    return MARKET_GROUPS

def get_signal_relationships() -> Dict[str, List[Dict[str, str]]]:
    """Get signal relationships."""
    return SIGNAL_RELATIONSHIPS

def get_markets_by_group(group: str) -> List[str]:
    """Get markets in a specific group."""
    return MARKET_GROUPS.get(group, [])

