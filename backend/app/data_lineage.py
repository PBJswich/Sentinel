"""
Data lineage tracking.

Tracks where data comes from and how it flows through the system.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class LineageRecord:
    """Data lineage record."""
    entity_id: str
    entity_type: str  # "signal", "snapshot", "composite"
    source: str  # "yahoo_finance", "fred_api", "composite", "manual"
    source_id: Optional[str] = None  # Original source identifier
    transformation: Optional[str] = None  # What transformation was applied
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)

# Lineage storage: {entity_id: LineageRecord}
_lineage: Dict[str, LineageRecord] = {}

def track_lineage(
    entity_id: str,
    entity_type: str,
    source: str,
    source_id: Optional[str] = None,
    transformation: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Track data lineage for an entity.
    
    Args:
        entity_id: Unique identifier for the entity
        entity_type: Type of entity (signal, snapshot, composite)
        source: Data source (yahoo_finance, fred_api, composite, manual)
        source_id: Original source identifier (e.g., symbol, series_id)
        transformation: Description of transformation applied
        metadata: Additional metadata
    """
    record = LineageRecord(
        entity_id=entity_id,
        entity_type=entity_type,
        source=source,
        source_id=source_id,
        transformation=transformation,
        metadata=metadata or {}
    )
    _lineage[entity_id] = record

def get_lineage(entity_id: str) -> Optional[Dict]:
    """Get lineage information for an entity."""
    record = _lineage.get(entity_id)
    if not record:
        return None
    
    return {
        "entity_id": record.entity_id,
        "entity_type": record.entity_type,
        "source": record.source,
        "source_id": record.source_id,
        "transformation": record.transformation,
        "created_at": record.created_at.isoformat(),
        "metadata": record.metadata
    }

def get_lineage_by_source(source: str) -> List[Dict]:
    """Get all entities from a specific source."""
    records = [r for r in _lineage.values() if r.source == source]
    return [
        {
            "entity_id": r.entity_id,
            "entity_type": r.entity_type,
            "source_id": r.source_id,
            "transformation": r.transformation,
            "created_at": r.created_at.isoformat()
        }
        for r in records
    ]

def get_lineage_summary() -> Dict:
    """Get lineage summary statistics."""
    by_source = defaultdict(int)
    by_type = defaultdict(int)
    
    for record in _lineage.values():
        by_source[record.source] += 1
        by_type[record.entity_type] += 1
    
    return {
        "total_entities": len(_lineage),
        "by_source": dict(by_source),
        "by_type": dict(by_type)
    }

