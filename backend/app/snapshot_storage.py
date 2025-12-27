"""
In-memory snapshot storage for signal history.

Stores historical snapshots of signals for point-in-time queries and change tracking.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional
from .models import Signal, SignalSnapshot
from .signal_loader import get_all_signals

# In-memory storage: maps (signal_id, date) -> SignalSnapshot
_snapshots: Dict[tuple[str, date], SignalSnapshot] = {}

def create_daily_snapshot(snapshot_date: Optional[date] = None) -> List[SignalSnapshot]:
    """
    Create daily snapshot of all current signals.
    
    Args:
        snapshot_date: Date for snapshot (defaults to today)
        
    Returns:
        List of created snapshots
    """
    if snapshot_date is None:
        snapshot_date = date.today()
    
    signals = get_all_signals()
    snapshots = []
    
    for signal in signals:
        snapshot_key = (signal.signal_id, snapshot_date)
        snapshot = SignalSnapshot(
            signal_id=signal.signal_id,
            snapshot_date=snapshot_date,
            signal=signal
        )
        _snapshots[snapshot_key] = snapshot
        snapshots.append(snapshot)
    
    return snapshots

def get_signal_history(signal_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[SignalSnapshot]:
    """
    Get historical snapshots for a specific signal.
    
    Args:
        signal_id: Signal ID to get history for
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        List of snapshots sorted by date (oldest first)
    """
    snapshots = []
    
    for (sid, snap_date), snapshot in _snapshots.items():
        if sid == signal_id:
            if start_date and snap_date < start_date:
                continue
            if end_date and snap_date > end_date:
                continue
            snapshots.append(snapshot)
    
    return sorted(snapshots, key=lambda s: s.snapshot_date)

def get_signals_at_date(target_date: date) -> List[Signal]:
    """
    Get all signals as they were at a specific date.
    
    Args:
        target_date: Date to query
        
    Returns:
        List of signals at that date
    """
    # Group snapshots by signal_id, keeping only the latest on or before target_date
    signal_snapshots = {}
    
    for (signal_id, snap_date), snapshot in _snapshots.items():
        if snap_date <= target_date:
            if signal_id not in signal_snapshots or snap_date > signal_snapshots[signal_id].snapshot_date:
                signal_snapshots[signal_id] = snapshot
    
    # Convert to list of signals
    signals = [snapshot.signal for snapshot in signal_snapshots.values()]
    
    # If no snapshots exist for that date, return current signals
    if not signals:
        return get_all_signals()
    
    return signals

def get_changes_since(since_date: date) -> Dict[str, List[Dict]]:
    """
    Get all signal changes since a specific date.
    
    Args:
        since_date: Date to compare against
        
    Returns:
        Dictionary with changes grouped by type
    """
    current_signals = {s.signal_id: s for s in get_all_signals()}
    
    # Get snapshots from since_date
    historical_signals = {}
    for (signal_id, snap_date), snapshot in _snapshots.items():
        if snap_date == since_date:
            historical_signals[signal_id] = snapshot.signal
    
    changes = {
        "new_signals": [],
        "changed_direction": [],
        "changed_confidence": [],
        "removed_signals": []
    }
    
    # Find new signals
    for signal_id, signal in current_signals.items():
        if signal_id not in historical_signals:
            changes["new_signals"].append({
                "signal_id": signal_id,
                "signal_name": signal.name,
                "market": signal.market,
                "direction": signal.direction.value,
                "confidence": signal.confidence.value
            })
    
    # Find changed signals
    for signal_id, current_signal in current_signals.items():
        if signal_id in historical_signals:
            historical_signal = historical_signals[signal_id]
            
            if current_signal.direction != historical_signal.direction:
                changes["changed_direction"].append({
                    "signal_id": signal_id,
                    "signal_name": current_signal.name,
                    "market": current_signal.market,
                    "old_direction": historical_signal.direction.value,
                    "new_direction": current_signal.direction.value
                })
            
            if current_signal.confidence != historical_signal.confidence:
                changes["changed_confidence"].append({
                    "signal_id": signal_id,
                    "signal_name": current_signal.name,
                    "market": current_signal.market,
                    "old_confidence": historical_signal.confidence.value,
                    "new_confidence": current_signal.confidence.value
                })
    
    # Find removed signals
    for signal_id, historical_signal in historical_signals.items():
        if signal_id not in current_signals:
            changes["removed_signals"].append({
                "signal_id": signal_id,
                "signal_name": historical_signal.name,
                "market": historical_signal.market
            })
    
    return changes

def initialize_snapshots():
    """Initialize with today's snapshot if none exist."""
    if not _snapshots:
        create_daily_snapshot()

