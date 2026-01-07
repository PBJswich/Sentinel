"""
Monitoring and logging utilities.

Basic monitoring for API health, performance, and errors.
"""

import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class RequestMetric:
    """Request metric data."""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

# In-memory metrics storage
_metrics: deque = deque(maxlen=10000)  # Keep last 10k requests
_error_logs: deque = deque(maxlen=1000)  # Keep last 1k errors
_endpoint_stats: Dict[str, Dict] = defaultdict(lambda: {
    "count": 0,
    "total_duration": 0.0,
    "errors": 0,
    "last_request": None
})

def record_request(endpoint: str, method: str, status_code: int, duration_ms: float):
    """Record a request metric."""
    metric = RequestMetric(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms
    )
    _metrics.append(metric)
    
    # Update endpoint stats
    key = f"{method} {endpoint}"
    stats = _endpoint_stats[key]
    stats["count"] += 1
    stats["total_duration"] += duration_ms
    stats["last_request"] = datetime.utcnow()
    
    if status_code >= 400:
        stats["errors"] += 1
        _error_logs.append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "timestamp": datetime.utcnow()
        })

def get_metrics(since_minutes: int = 60) -> Dict:
    """Get metrics for the last N minutes."""
    cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
    
    recent_metrics = [m for m in _metrics if m.timestamp >= cutoff]
    
    if not recent_metrics:
        return {
            "total_requests": 0,
            "avg_duration_ms": 0,
            "error_rate": 0,
            "endpoints": {}
        }
    
    total = len(recent_metrics)
    errors = sum(1 for m in recent_metrics if m.status_code >= 400)
    avg_duration = sum(m.duration_ms for m in recent_metrics) / total
    
    # Endpoint breakdown
    endpoint_counts = defaultdict(int)
    for m in recent_metrics:
        endpoint_counts[f"{m.method} {m.endpoint}"] += 1
    
    return {
        "total_requests": total,
        "avg_duration_ms": round(avg_duration, 2),
        "error_rate": round(errors / total * 100, 2) if total > 0 else 0,
        "errors": errors,
        "endpoints": dict(endpoint_counts),
        "period_minutes": since_minutes
    }

def get_endpoint_stats() -> Dict[str, Dict]:
    """Get statistics per endpoint."""
    stats = {}
    for endpoint, data in _endpoint_stats.items():
        count = data["count"]
        avg_duration = data["total_duration"] / count if count > 0 else 0
        stats[endpoint] = {
            "count": count,
            "avg_duration_ms": round(avg_duration, 2),
            "errors": data["errors"],
            "error_rate": round(data["errors"] / count * 100, 2) if count > 0 else 0,
            "last_request": data["last_request"].isoformat() if data["last_request"] else None
        }
    return stats

def get_recent_errors(limit: int = 50) -> List[Dict]:
    """Get recent error logs."""
    return list(_error_logs)[-limit:]

def clear_metrics():
    """Clear all metrics (for testing/reset)."""
    _metrics.clear()
    _error_logs.clear()
    _endpoint_stats.clear()

