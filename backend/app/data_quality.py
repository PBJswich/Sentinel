"""
Data quality monitoring.

Tracks data freshness, completeness, and validation results.
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class QualityMetric:
    """Data quality metric."""
    signal_id: str
    market: str
    category: str
    freshness_days: int
    is_stale: bool
    has_score: bool
    validation_errors: List[str]
    last_updated: date

# Quality metrics storage
_quality_metrics: Dict[str, QualityMetric] = {}

def assess_signal_quality(signal) -> QualityMetric:
    """
    Assess quality of a signal.
    
    Args:
        signal: Signal object
        
    Returns:
        QualityMetric
    """
    freshness_days = (date.today() - signal.data_asof).days
    
    validation_errors = []
    if not signal.explanation or len(signal.explanation) < 10:
        validation_errors.append("Explanation too short")
    if not signal.definition:
        validation_errors.append("Missing definition")
    if signal.score is None:
        # Score can be calculated, so this is a warning not an error
        pass
    
    metric = QualityMetric(
        signal_id=signal.signal_id,
        market=signal.market,
        category=signal.category,
        freshness_days=freshness_days,
        is_stale=signal.is_stale,
        has_score=signal.score is not None,
        validation_errors=validation_errors,
        last_updated=signal.last_updated
    )
    
    _quality_metrics[signal.signal_id] = metric
    return metric

def get_quality_summary() -> Dict:
    """Get overall data quality summary."""
    if not _quality_metrics:
        return {
            "total_signals": 0,
            "stale_signals": 0,
            "signals_with_errors": 0,
            "avg_freshness_days": 0,
            "by_category": {},
            "by_market": {}
        }
    
    total = len(_quality_metrics)
    stale = sum(1 for m in _quality_metrics.values() if m.is_stale)
    with_errors = sum(1 for m in _quality_metrics.values() if m.validation_errors)
    avg_freshness = sum(m.freshness_days for m in _quality_metrics.values()) / total
    
    # Breakdown by category
    by_category = defaultdict(lambda: {"total": 0, "stale": 0, "errors": 0})
    for m in _quality_metrics.values():
        cat = by_category[m.category]
        cat["total"] += 1
        if m.is_stale:
            cat["stale"] += 1
        if m.validation_errors:
            cat["errors"] += 1
    
    # Breakdown by market
    by_market = defaultdict(lambda: {"total": 0, "stale": 0, "errors": 0})
    for m in _quality_metrics.values():
        mkt = by_market[m.market]
        mkt["total"] += 1
        if m.is_stale:
            mkt["stale"] += 1
        if m.validation_errors:
            mkt["errors"] += 1
    
    return {
        "total_signals": total,
        "stale_signals": stale,
        "stale_percentage": round(stale / total * 100, 2) if total > 0 else 0,
        "signals_with_errors": with_errors,
        "error_percentage": round(with_errors / total * 100, 2) if total > 0 else 0,
        "avg_freshness_days": round(avg_freshness, 1),
        "by_category": {k: dict(v) for k, v in by_category.items()},
        "by_market": {k: dict(v) for k, v in by_market.items()}
    }

def get_quality_issues(limit: int = 50) -> List[Dict]:
    """Get signals with quality issues."""
    issues = []
    for metric in _quality_metrics.values():
        if metric.is_stale or metric.validation_errors:
            issues.append({
                "signal_id": metric.signal_id,
                "market": metric.market,
                "category": metric.category,
                "issues": (
                    ["stale"] if metric.is_stale else []
                ) + metric.validation_errors,
                "freshness_days": metric.freshness_days,
                "last_updated": metric.last_updated.isoformat()
            })
    
    # Sort by freshness (oldest first)
    issues.sort(key=lambda x: x["freshness_days"], reverse=True)
    return issues[:limit]

