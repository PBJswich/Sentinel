"""
In-memory alert storage and evaluation.

Stores alert configurations and evaluates them against current signal state.
"""

from typing import Dict, List, Optional
from datetime import date, timedelta
from .models import Alert, AlertType, Signal, Direction, Confidence
from .signal_loader import get_all_signals
from .conflict_detector import get_all_conflicts
from .snapshot_storage import get_changes_since, get_regime_at_date, detect_regime_transition
from .regime_detector import detect_regime

# In-memory storage: maps alert_id -> Alert
_alerts: Dict[str, Alert] = {}

def create_alert(alert: Alert) -> Alert:
    """Create a new alert."""
    _alerts[alert.alert_id] = alert
    return alert

def get_alert(alert_id: str) -> Optional[Alert]:
    """Get an alert by ID."""
    return _alerts.get(alert_id)

def get_all_alerts() -> List[Alert]:
    """Get all alerts."""
    return list(_alerts.values())

def update_alert(alert_id: str, alert: Alert) -> Optional[Alert]:
    """Update an existing alert."""
    if alert_id not in _alerts:
        return None
    _alerts[alert_id] = alert
    return alert

def delete_alert(alert_id: str) -> bool:
    """Delete an alert."""
    if alert_id in _alerts:
        del _alerts[alert_id]
        return True
    return False

def evaluate_alert(alert: Alert) -> Optional[Dict]:
    """
    Evaluate an alert against current signal state.
    
    Returns alert trigger information if alert fires, None otherwise.
    """
    if not alert.enabled:
        return None
    
    signals = get_all_signals()
    signal_map = {s.signal_id: s for s in signals}
    
    if alert.alert_type == AlertType.DIRECTION_CHANGE:
        # Check if any signal changed direction since last check
        conditions = alert.conditions
        signal_id = conditions.get("signal_id")
        if signal_id and signal_id in signal_map:
            # Get changes since last triggered (or yesterday if never triggered)
            since_date = alert.last_triggered or (date.today() - timedelta(days=1))
            changes = get_changes_since(since_date)
            
            for change in changes.get("changed_direction", []):
                if change["signal_id"] == signal_id:
                    alert.last_triggered = date.today()
                    return {
                        "alert_id": alert.alert_id,
                        "alert_name": alert.name,
                        "triggered": True,
                        "trigger_reason": f"Signal {change['signal_name']} changed direction from {change['old_direction']} to {change['new_direction']}",
                        "signal_id": signal_id,
                        "change": change
                    }
    
    elif alert.alert_type == AlertType.CONFIDENCE_CHANGE:
        # Check if any signal changed confidence
        conditions = alert.conditions
        signal_id = conditions.get("signal_id")
        if signal_id and signal_id in signal_map:
            since_date = alert.last_triggered or (date.today() - timedelta(days=1))
            changes = get_changes_since(since_date)
            
            for change in changes.get("changed_confidence", []):
                if change["signal_id"] == signal_id:
                    alert.last_triggered = date.today()
                    return {
                        "alert_id": alert.alert_id,
                        "alert_name": alert.name,
                        "triggered": True,
                        "trigger_reason": f"Signal {change['signal_name']} changed confidence from {change['old_confidence']} to {change['new_confidence']}",
                        "signal_id": signal_id,
                        "change": change
                    }
    
    elif alert.alert_type == AlertType.NEW_CONFLICT:
        # Check if new conflicts detected
        conditions = alert.conditions
        market = conditions.get("market")  # Optional market filter
        
        conflicts = get_all_conflicts()
        if market:
            conflicts = [c for c in conflicts if c.market == market]
        
        # Check if conflicts are new (since last triggered)
        since_date = alert.last_triggered or (date.today() - timedelta(days=1))
        if conflicts:
            # For simplicity, trigger if any conflicts exist (could be enhanced to track specific conflicts)
            alert.last_triggered = date.today()
            return {
                "alert_id": alert.alert_id,
                "alert_name": alert.name,
                "triggered": True,
                "trigger_reason": f"{len(conflicts)} conflict(s) detected",
                "conflicts": [c.model_dump() for c in conflicts[:5]]  # Limit to 5
            }
    
    elif alert.alert_type == AlertType.REGIME_TRANSITION:
        # Check for regime transition
        current_regime = detect_regime()
        previous_regime = get_regime_at_date(date.today() - timedelta(days=1))
        transition = detect_regime_transition(current_regime, previous_regime)
        
        if transition:
            alert.last_triggered = date.today()
            return {
                "alert_id": alert.alert_id,
                "alert_name": alert.name,
                "triggered": True,
                "trigger_reason": transition["description"],
                "transition": transition
            }
    
    elif alert.alert_type == AlertType.STALE_SIGNAL:
        # Check for stale signals
        conditions = alert.conditions
        market = conditions.get("market")  # Optional market filter
        
        stale_signals = [s for s in signals if s.is_stale]
        if market:
            stale_signals = [s for s in stale_signals if s.market == market]
        
        if stale_signals:
            alert.last_triggered = date.today()
            return {
                "alert_id": alert.alert_id,
                "alert_name": alert.name,
                "triggered": True,
                "trigger_reason": f"{len(stale_signals)} stale signal(s) detected",
                "stale_signals": [
                    {
                        "signal_id": s.signal_id,
                        "signal_name": s.name,
                        "market": s.market,
                        "age_days": s.age_days
                    }
                    for s in stale_signals[:10]  # Limit to 10
                ]
            }
    
    return None

def evaluate_all_alerts() -> List[Dict]:
    """Evaluate all enabled alerts and return triggered ones."""
    triggered = []
    for alert in _alerts.values():
        if alert.enabled:
            result = evaluate_alert(alert)
            if result:
                triggered.append(result)
    return triggered

