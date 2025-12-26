"""
Signal loader with hot-reload support.

Loads signals from JSON file and supports hot-reload for local development.
Simulates daily updates by calculating timestamps dynamically.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional
from .models import Signal, Direction, Confidence, ValidityWindow, SignalType
from .registry import get_registry

# Cache for loaded signals and file modification time
_cached_signals: Optional[List[Signal]] = None
_cached_file_mtime: Optional[float] = None

def _get_signals_file_path() -> Path:
    """Get the path to the signals JSON file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "data" / "signals.json"

def _load_signals_from_file() -> List[Signal]:
    """Load signals from JSON file and convert to Signal objects."""
    signals_file = _get_signals_file_path()
    
    if not signals_file.exists():
        raise FileNotFoundError(f"Signals file not found: {signals_file}")
    
    with open(signals_file, 'r', encoding='utf-8') as f:
        signals_data = json.load(f)
    
    registry = get_registry()
    today = date.today()
    
    signals = []
    for signal_data in signals_data:
        signal_id = signal_data["signal_id"]
        registry_entry = registry.get(signal_id, {})
        
        # Calculate dates based on offsets 
        data_asof_offset = signal_data.get("data_asof_offset_days", 1)
        data_asof = today - timedelta(days=data_asof_offset)
        last_updated = today  
        
        # Get direction and confidence enums
        direction = Direction[signal_data["direction"].upper()]
        confidence = Confidence[signal_data["confidence"].upper()]
        validity_window = ValidityWindow[signal_data.get("validity_window", registry_entry.get("validity_window", "daily")).upper()]
        signal_type = SignalType[signal_data.get("signal_type", registry_entry.get("signal_type", "tactical")).upper()]
        
        signal = Signal(
            signal_id=signal_data["signal_id"],
            version=signal_data.get("version", registry_entry.get("version", "v1")),
            market=signal_data["market"],
            category=signal_data["category"],
            name=signal_data["name"],
            direction=direction,
            confidence=confidence,
            last_updated=last_updated,
            data_asof=data_asof,
            explanation=signal_data["explanation"],
            definition=signal_data["definition"],
            source=signal_data["source"],
            key_driver=signal_data.get("key_driver", registry_entry.get("key_driver", "")),
            validity_window=validity_window,
            decay_behavior=signal_data.get("decay_behavior", registry_entry.get("decay_behavior", "")),
            related_signal_ids=signal_data.get("related_signal_ids", registry_entry.get("related_signal_ids", [])),
            related_markets=signal_data.get("related_markets", registry_entry.get("related_markets", [])),
            signal_type=signal_type
        )
        signals.append(signal)
    
    return signals

def get_all_signals(force_reload: bool = False) -> List[Signal]:
    """
    Get all signals, with hot-reload support for local development.
    
    Args:
        force_reload: If True, force reload from file regardless of cache.
    
    Returns:
        List of Signal objects.
    """
    global _cached_signals, _cached_file_mtime
    
    signals_file = _get_signals_file_path()
    
    # Check if file exists and get modification time
    if signals_file.exists():
        current_mtime = os.path.getmtime(signals_file)
    else:
        current_mtime = 0
    
    # Hot-reload: check if file has been modified or cache is empty
    if force_reload or _cached_signals is None or _cached_file_mtime != current_mtime:
        _cached_signals = _load_signals_from_file()
        _cached_file_mtime = current_mtime
    
    return _cached_signals

def reload_signals() -> List[Signal]:
    """Force reload signals from file (useful for testing or manual refresh)."""
    return get_all_signals(force_reload=True)

