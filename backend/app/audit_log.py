"""
Audit logging for signal changes and system actions.

Tracks what changed, when, and why for full traceability.
"""

from datetime import date, datetime
from typing import Dict, List, Optional
from enum import Enum

class ChangeType(str, Enum):
    """Types of changes that can be logged."""
    SIGNAL_CREATED = "signal_created"
    SIGNAL_UPDATED = "signal_updated"
    SIGNAL_DELETED = "signal_deleted"
    DIRECTION_CHANGED = "direction_changed"
    CONFIDENCE_CHANGED = "confidence_changed"
    REGIME_CHANGED = "regime_changed"
    CONFLICT_DETECTED = "conflict_detected"

class AuditLogEntry:
    """Single audit log entry."""
    def __init__(
        self,
        change_type: ChangeType,
        entity_id: str,
        entity_type: str,
        description: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ):
        self.change_type = change_type
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.description = description
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_type": self.change_type.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat()
        }

# In-memory audit log storage
_audit_log: List[AuditLogEntry] = []

def log_change(
    change_type: ChangeType,
    entity_id: str,
    entity_type: str,
    description: str,
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None
):
    """Log a change to the audit log."""
    entry = AuditLogEntry(
        change_type=change_type,
        entity_id=entity_id,
        entity_type=entity_type,
        description=description,
        old_value=old_value,
        new_value=new_value
    )
    _audit_log.append(entry)
    
    # Keep only last 1000 entries (prevent unbounded growth)
    if len(_audit_log) > 1000:
        _audit_log.pop(0)

def get_audit_log(
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    change_type: Optional[ChangeType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict]:
    """
    Get audit log entries with optional filtering.
    
    Args:
        entity_id: Filter by entity ID
        entity_type: Filter by entity type
        change_type: Filter by change type
        start_date: Filter by start date
        end_date: Filter by end date
        
    Returns:
        List of audit log entries as dictionaries
    """
    filtered = _audit_log
    
    if entity_id:
        filtered = [e for e in filtered if e.entity_id == entity_id]
    
    if entity_type:
        filtered = [e for e in filtered if e.entity_type == entity_type]
    
    if change_type:
        filtered = [e for e in filtered if e.change_type == change_type]
    
    if start_date:
        filtered = [e for e in filtered if e.timestamp.date() >= start_date]
    
    if end_date:
        filtered = [e for e in filtered if e.timestamp.date() <= end_date]
    
    # Sort by timestamp (newest first)
    filtered.sort(key=lambda e: e.timestamp, reverse=True)
    
    return [e.to_dict() for e in filtered]

def get_changes_for_entity(entity_id: str, entity_type: str) -> List[Dict]:
    """Get all changes for a specific entity."""
    return get_audit_log(entity_id=entity_id, entity_type=entity_type)

