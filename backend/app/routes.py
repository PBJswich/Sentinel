from typing import Optional, List, Dict
from datetime import date
from fastapi import APIRouter, Query, HTTPException
from .models import Signal, Direction, Confidence, SignalsResponse, SignalRelationship, RelationshipType, Conflict, SignalSnapshot
from .signal_loader import get_all_signals, reload_signals
from .conflict_detector import get_all_conflicts, get_conflicts_for_market
from .registry import get_signal_relationships
from .snapshot_storage import (
    create_daily_snapshot,
    get_signal_history,
    get_signals_at_date,
    get_changes_since,
    initialize_snapshots
)

router = APIRouter()

# Initialize snapshots on module load
initialize_snapshots()

def _get_all_signals():
    """Returns all signals loaded from JSON file with hot-reload support."""
    return get_all_signals()

def _filter_signals(signals: list[Signal], market: Optional[str] = None, category: Optional[str] = None) -> list[Signal]:
    """Filter signals by market and/or category (case-insensitive)."""
    filtered = signals
    
    if market:
        market_lower = market.lower().strip()
        filtered = [s for s in filtered if s.market.lower() == market_lower]
    
    if category:
        category_lower = category.lower().strip()
        filtered = [s for s in filtered if s.category.lower() == category_lower]
    
    return filtered

def _get_stale_warnings(signals: list[Signal]) -> Optional[List[Dict]]:
    """Get stale signal warnings for a list of signals."""
    warnings = []
    for signal in signals:
        if signal.is_stale:
            warnings.append({
                "signal_id": signal.signal_id,
                "signal_name": signal.name,
                "market": signal.market,
                "age_days": signal.age_days,
                "validity_window": signal.validity_window.value,
                "warning": f"Signal is {signal.age_days} days old, exceeding {signal.validity_window.value} validity window"
            })
    return warnings if warnings else None

@router.get("/signals", response_model=SignalsResponse)
def get_signals(
    market: Optional[str] = Query(None, description="Filter by market name (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by category (case-insensitive)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of signals to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of signals to skip")
):
    """
    Get signals with optional filtering by market and/or category.
    
    - **market**: Filter by market name (case-insensitive, e.g., "wti crude oil", "Gold")
    - **category**: Filter by category (case-insensitive, e.g., "technical", "Macro", "Fundamental", "Sentiment")
    - **limit**: Maximum number of signals to return (pagination)
    - **offset**: Number of signals to skip (pagination)
    
    Returns empty signals list if no signals match the filters.
    """
    all_signals = _get_all_signals()
    total = len(all_signals)
    
    # Apply filters (case-insensitive)
    filtered_signals = _filter_signals(all_signals, market, category)
    filtered_count = len(filtered_signals)
    
    # Apply pagination
    if offset is not None:
        filtered_signals = filtered_signals[offset:]
    if limit is not None:
        filtered_signals = filtered_signals[:limit]
    
    stale_warnings = _get_stale_warnings(filtered_signals)
    
    return SignalsResponse(
        signals=filtered_signals,
        total=total,
        filtered_count=filtered_count,
        limit=limit,
        offset=offset,
        stale_warnings=stale_warnings
    )

@router.get("/signals/{market}", response_model=SignalsResponse)
def get_signals_by_market(
    market: str,
    category: Optional[str] = Query(None, description="Optional category filter (case-insensitive)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of signals to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of signals to skip")
):
    """
    Get signals for a specific market.
    
    - **market**: Market name (case-insensitive, e.g., "wti crude oil", "Gold")
    - **category**: Optional category filter (case-insensitive)
    - **limit**: Maximum number of signals to return (pagination)
    - **offset**: Number of signals to skip (pagination)
    
    Returns empty signals list if market not found or no signals match.
    """
    all_signals = _get_all_signals()
    total = len(all_signals)
    
    # Filter by market (case-insensitive) and optional category
    filtered_signals = _filter_signals(all_signals, market, category)
    filtered_count = len(filtered_signals)
    
    # Apply pagination
    if offset is not None:
        filtered_signals = filtered_signals[offset:]
    if limit is not None:
        filtered_signals = filtered_signals[:limit]
    
    stale_warnings = _get_stale_warnings(filtered_signals)
    
    return SignalsResponse(
        signals=filtered_signals,
        total=total,
        filtered_count=filtered_count,
        limit=limit,
        offset=offset,
        stale_warnings=stale_warnings
    )

@router.get("/markets")
def get_markets():
    """
    Get list of unique markets that have signals, including their group information.
    
    Returns a list of markets with their group assignments.
    """
    from .registry import get_market_groups
    
    signals = _get_all_signals()
    markets_set = set(s.market for s in signals)
    market_groups = get_market_groups()
    
    # Build reverse mapping: market -> groups
    market_to_groups = {}
    for group_name, markets in market_groups.items():
        for market in markets:
            if market in markets_set:
                if market not in market_to_groups:
                    market_to_groups[market] = []
                market_to_groups[market].append(group_name)
    
    # Build response with group info
    markets_list = []
    for market in sorted(markets_set):
        markets_list.append({
            "market": market,
            "groups": sorted(market_to_groups.get(market, []))
        })
    
    return {
        "markets": markets_list,
        "total_markets": len(markets_set)
    }

@router.get("/markets/{market}/summary")
def get_market_summary(market: str):
    """
    Get comprehensive summary for a specific market.
    
    Provides aggregated analysis including:
    - Signal counts by direction, confidence, and pillar
    - Dominant forces (highest confidence signals)
    - Conflicts for the market
    - Confidence distribution
    - Human-readable market narrative
    
    - **market**: Market name (case-insensitive)
    """
    all_signals = _get_all_signals()
    market_signals = [s for s in all_signals if s.market.lower() == market.lower()]
    
    if not market_signals:
        raise HTTPException(status_code=404, detail=f"Market '{market}' not found or has no signals")
    
    # Count by direction
    direction_counts = {
        "bullish": sum(1 for s in market_signals if s.direction == Direction.BULLISH),
        "bearish": sum(1 for s in market_signals if s.direction == Direction.BEARISH),
        "neutral": sum(1 for s in market_signals if s.direction == Direction.NEUTRAL)
    }
    
    # Count by confidence
    confidence_counts = {
        "high": sum(1 for s in market_signals if s.confidence == Confidence.HIGH),
        "medium": sum(1 for s in market_signals if s.confidence == Confidence.MEDIUM),
        "low": sum(1 for s in market_signals if s.confidence == Confidence.LOW)
    }
    
    # Count by pillar (category)
    pillar_counts = {}
    for signal in market_signals:
        pillar = signal.category
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
    
    # Identify dominant forces (highest confidence signals)
    dominant_forces = sorted(
        market_signals,
        key=lambda s: (
            3 if s.confidence == Confidence.HIGH else (2 if s.confidence == Confidence.MEDIUM else 1),
            s.direction.value
        ),
        reverse=True
    )[:5]  # Top 5
    
    # Get conflicts for this market
    market_conflicts = get_conflicts_for_market(market)
    
    # Calculate confidence distribution
    total_signals = len(market_signals)
    confidence_distribution = {
        "high_pct": round((confidence_counts["high"] / total_signals * 100) if total_signals > 0 else 0, 1),
        "medium_pct": round((confidence_counts["medium"] / total_signals * 100) if total_signals > 0 else 0, 1),
        "low_pct": round((confidence_counts["low"] / total_signals * 100) if total_signals > 0 else 0, 1)
    }
    
    # Generate human-readable narrative
    narrative_parts = []
    narrative_parts.append(f"{market} has {total_signals} active signal(s).")
    
    # Direction summary
    if direction_counts["bullish"] > direction_counts["bearish"]:
        narrative_parts.append(f"Signals are predominantly bullish ({direction_counts['bullish']} bullish vs {direction_counts['bearish']} bearish).")
    elif direction_counts["bearish"] > direction_counts["bullish"]:
        narrative_parts.append(f"Signals are predominantly bearish ({direction_counts['bearish']} bearish vs {direction_counts['bullish']} bullish).")
    else:
        narrative_parts.append(f"Signals are mixed ({direction_counts['bullish']} bullish, {direction_counts['bearish']} bearish, {direction_counts['neutral']} neutral).")
    
    # Confidence summary
    if confidence_counts["high"] > 0:
        narrative_parts.append(f"{confidence_counts['high']} high-confidence signal(s) provide strong directional bias.")
    
    # Pillar summary
    pillar_list = ", ".join([f"{count} {pillar}" for pillar, count in sorted(pillar_counts.items())])
    narrative_parts.append(f"Signals span {len(pillar_counts)} pillar(s): {pillar_list}.")
    
    # Conflicts
    if market_conflicts:
        narrative_parts.append(f"⚠️ {len(market_conflicts)} conflict(s) detected - contradictory forces are present.")
    
    # Stale signals
    stale_count = sum(1 for s in market_signals if s.is_stale)
    if stale_count > 0:
        narrative_parts.append(f"⚠️ {stale_count} signal(s) are stale and may need updating.")
    
    narrative = " ".join(narrative_parts)
    
    # Get market group
    from .registry import get_market_groups
    market_groups = get_market_groups()
    market_group = None
    for group_name, markets in market_groups.items():
        if market in markets:
            market_group = group_name
            break
    
    return {
        "market": market,
        "market_group": market_group,
        "total_signals": total_signals,
        "direction_breakdown": direction_counts,
        "confidence_breakdown": confidence_counts,
        "pillar_breakdown": pillar_counts,
        "confidence_distribution": confidence_distribution,
        "dominant_forces": [
            {
                "signal_id": s.signal_id,
                "signal_name": s.name,
                "category": s.category,
                "direction": s.direction.value,
                "confidence": s.confidence.value,
                "explanation": s.explanation
            }
            for s in dominant_forces
        ],
        "conflicts": [c.model_dump() for c in market_conflicts],
        "conflict_count": len(market_conflicts),
        "narrative": narrative,
        "signals": [
            {
                "signal_id": s.signal_id,
                "name": s.name,
                "category": s.category,
                "direction": s.direction.value,
                "confidence": s.confidence.value,
                "is_stale": s.is_stale,
                "age_days": s.age_days
            }
            for s in market_signals
        ]
    }

@router.get("/markets/groups/{group}")
def get_market_group_summary(group: str):
    """
    Get summary for a market group (energy, metals, ags).
    
    Aggregates signals across all markets in the group and provides:
    - Total signals across group
    - Direction breakdown across group
    - Markets in the group with signal counts
    - Group-level conflicts
    
    - **group**: Market group name (energy, metals, ags) - case-insensitive
    """
    from .registry import get_markets_by_group
    
    markets_in_group = get_markets_by_group(group.lower())
    
    if not markets_in_group:
        raise HTTPException(status_code=404, detail=f"Market group '{group}' not found")
    
    all_signals = _get_all_signals()
    group_signals = [s for s in all_signals if s.market in markets_in_group]
    
    # Count by direction across group
    direction_counts = {
        "bullish": sum(1 for s in group_signals if s.direction == Direction.BULLISH),
        "bearish": sum(1 for s in group_signals if s.direction == Direction.BEARISH),
        "neutral": sum(1 for s in group_signals if s.direction == Direction.NEUTRAL)
    }
    
    # Count by confidence
    confidence_counts = {
        "high": sum(1 for s in group_signals if s.confidence == Confidence.HIGH),
        "medium": sum(1 for s in group_signals if s.confidence == Confidence.MEDIUM),
        "low": sum(1 for s in group_signals if s.confidence == Confidence.LOW)
    }
    
    # Count by pillar
    pillar_counts = {}
    for signal in group_signals:
        pillar = signal.category
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
    
    # Get signals per market
    signals_by_market = {}
    for market in markets_in_group:
        market_sigs = [s for s in group_signals if s.market == market]
        signals_by_market[market] = {
            "total_signals": len(market_sigs),
            "direction_breakdown": {
                "bullish": sum(1 for s in market_sigs if s.direction == Direction.BULLISH),
                "bearish": sum(1 for s in market_sigs if s.direction == Direction.BEARISH),
                "neutral": sum(1 for s in market_sigs if s.direction == Direction.NEUTRAL)
            }
        }
    
    # Get conflicts across group
    group_conflicts = []
    for market in markets_in_group:
        market_conflicts = get_conflicts_for_market(market)
        group_conflicts.extend(market_conflicts)
    
    return {
        "group": group.lower(),
        "markets": markets_in_group,
        "total_markets": len(markets_in_group),
        "total_signals": len(group_signals),
        "direction_breakdown": direction_counts,
        "confidence_breakdown": confidence_counts,
        "pillar_breakdown": pillar_counts,
        "markets_summary": signals_by_market,
        "conflicts": [c.model_dump() for c in group_conflicts],
        "conflict_count": len(group_conflicts)
    }

@router.get("/categories")
def get_categories():
    """
    Get list of unique signal categories.
    
    Returns a list of category names sorted alphabetically.
    """
    signals = _get_all_signals()
    categories = sorted(set(s.category for s in signals))
    return {"categories": categories}

@router.get("/registry")
def get_signal_registry():
    """
    Get the signal registry with all registered signal IDs, metadata, relationships, and market groups.
    
    Returns the internal signal registry showing:
    - Stable identifiers, versions, and metadata for all signals
    - Signal relationships (which signals relate to which)
    - Market groupings (energy, metals, ags)
    """
    from .registry import (
        get_registry, 
        list_all_signal_ids,
        get_signal_relationships,
        get_market_groups
    )
    
    registry = get_registry()
    signal_ids = list_all_signal_ids()
    relationships = get_signal_relationships()
    market_groups = get_market_groups()
    
    return {
        "registry_version": "v1",
        "total_signals": len(signal_ids),
        "signal_ids": signal_ids,
        "signals": registry,
        "relationships": relationships,
        "market_groups": market_groups
    }

@router.get("/signals/explain")
def explain_signals(
    market: Optional[str] = Query(None, description="Filter by market name (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by category (case-insensitive)")
):
    """
    Get human-readable summaries of signals with explainability information.
    Provides aggregated summaries showing:
    - Signal definitions and sources
    - Data freshness (last_updated vs data_asof)
    - Market and category breakdowns
    - Signal relationships
    - Conflicts
    - **market**: Filter by market name (case-insensitive)
    - **category**: Filter by category (case-insensitive)
    """
    all_signals = _get_all_signals()
    filtered_signals = _filter_signals(all_signals, market, category)
    
    if not filtered_signals:
        return {
            "summary": "No signals found matching the specified filters.",
            "signals": []
        }
    
    # Get conflicts for filtered signals
    conflicts = get_all_conflicts(filtered_signals)
    conflicts_by_market = {}
    for conflict in conflicts:
        if conflict.market:
            if conflict.market not in conflicts_by_market:
                conflicts_by_market[conflict.market] = []
            conflicts_by_market[conflict.market].append(conflict)
    
    # Group by market
    by_market = {}
    for signal in filtered_signals:
        if signal.market not in by_market:
            by_market[signal.market] = []
        by_market[signal.market].append(signal)
    
    # Group by category
    by_category = {}
    for signal in filtered_signals:
        if signal.category not in by_category:
            by_category[signal.category] = []
        by_category[signal.category].append(signal)
    
    # Build summaries
    market_summaries = []
    for market_name, signals in by_market.items():
        bullish = sum(1 for s in signals if s.direction == Direction.BULLISH)
        bearish = sum(1 for s in signals if s.direction == Direction.BEARISH)
        neutral = sum(1 for s in signals if s.direction == Direction.NEUTRAL)
        high_conf = sum(1 for s in signals if s.confidence == Confidence.HIGH)
        
        # Get relationships for signals in this market
        market_relationships = []
        for s in signals:
            if s.related_signal_ids:
                market_relationships.append({
                    "signal_id": s.signal_id,
                    "signal_name": s.name,
                    "related_signals": s.related_signal_ids
                })
        
        # Get conflicts for this market
        market_conflicts = [c.model_dump() for c in conflicts_by_market.get(market_name, [])]
        
        market_summaries.append({
            "market": market_name,
            "total_signals": len(signals),
            "direction_breakdown": {
                "bullish": bullish,
                "bearish": bearish,
                "neutral": neutral
            },
            "high_confidence_count": high_conf,
            "conflicts": market_conflicts,
            "conflict_count": len(market_conflicts),
            "relationships": market_relationships,
            "signals": [
                {
                    "name": s.name,
                    "category": s.category,
                    "direction": s.direction.value,
                    "confidence": s.confidence.value,
                    "definition": s.definition,
                    "source": s.source,
                    "explanation": s.explanation,
                    "key_driver": s.key_driver,
                    "signal_id": s.signal_id,
                    "version": s.version,
                    "validity_window": s.validity_window.value,
                    "signal_type": s.signal_type.value,
                    "related_signal_ids": s.related_signal_ids,
                    "related_markets": s.related_markets,
                    "age_days": s.age_days,
                    "is_stale": s.is_stale,
                    "data_freshness": {
                        "status": s.data_freshness.value,
                        "last_updated": str(s.last_updated),
                        "data_asof": str(s.data_asof),
                        "days_old": (s.last_updated - s.data_asof).days
                    }
                }
                for s in signals
            ]
        })
    
    category_summaries = {}
    for category_name, signals in by_category.items():
        category_summaries[category_name] = {
            "count": len(signals),
            "sources": sorted(set(s.source for s in signals)),
            "signals": [s.name for s in signals]
        }
    
    return {
        "summary": f"Found {len(filtered_signals)} signal(s) across {len(by_market)} market(s) and {len(by_category)} category/categories.",
        "total_signals": len(filtered_signals),
        "total_conflicts": len(conflicts),
        "markets": market_summaries,
        "categories": category_summaries,
        "data_freshness_summary": {
            "most_recent_update": str(max(s.last_updated for s in filtered_signals)),
            "oldest_data": str(min(s.data_asof for s in filtered_signals)),
            "fresh_count": sum(1 for s in filtered_signals if s.data_freshness.value == "fresh"),
            "stale_count": sum(1 for s in filtered_signals if s.data_freshness.value == "stale"),
            "unknown_count": sum(1 for s in filtered_signals if s.data_freshness.value == "unknown")
        },
        "staleness_summary": {
            "stale_signals_count": sum(1 for s in filtered_signals if s.is_stale),
            "stale_warnings": _get_stale_warnings(filtered_signals) or []
        }
    }

@router.get("/signals/{signal_id}/relationships")
def get_signal_relationships_endpoint(signal_id: str):
    """
    Get relationships for a specific signal.
    
    Returns all signals related to the specified signal, including relationship types.
    """
    all_signals = _get_all_signals()
    signal_map = {s.signal_id: s for s in all_signals}
    
    if signal_id not in signal_map:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    signal = signal_map[signal_id]
    relationships = []
    
    # Get relationships from registry
    registry_relationships = get_signal_relationships()
    signal_rels = registry_relationships.get(signal_id, [])
    
    # Also check related_signal_ids from signal itself
    for related_id in signal.related_signal_ids:
        if related_id in signal_map:
            relationships.append(SignalRelationship(
                signal_id=related_id,
                relationship_type=RelationshipType.RELATED,
                description=f"Related signal: {signal_map[related_id].name}"
            ))
    
    # Add registry relationships
    for rel in signal_rels:
        related_id = rel.get("signal_id")
        rel_type = rel.get("relationship_type", "related")
        if related_id in signal_map:
            try:
                relationship_type = RelationshipType[rel_type.upper()]
            except KeyError:
                relationship_type = RelationshipType.RELATED
            
            relationships.append(SignalRelationship(
                signal_id=related_id,
                relationship_type=relationship_type,
                description=rel.get("description")
            ))
    
    return {
        "signal_id": signal_id,
        "signal_name": signal.name,
        "relationships": relationships
    }

@router.get("/signals/conflicts")
def get_conflicts_endpoint(
    market: Optional[str] = Query(None, description="Filter conflicts by market (case-insensitive)")
):
    """
    Get all detected conflicts between signals.
    
    Conflicts are detected based on rules:
    - Same market, opposite directions, high confidence
    - Structural vs tactical mismatch
    - Timeframe mismatch (intraday/daily vs structural)
    
    - **market**: Optional filter to get conflicts for a specific market
    """
    if market:
        conflicts = get_conflicts_for_market(market)
    else:
        conflicts = get_all_conflicts()
    
    return {
        "total_conflicts": len(conflicts),
        "conflicts": [conflict.model_dump() for conflict in conflicts]
    }

@router.get("/signals/{signal_id}/history")
def get_signal_history_endpoint(
    signal_id: str,
    start_date: Optional[date] = Query(None, description="Start date for history (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for history (YYYY-MM-DD)")
):
    """
    Get historical snapshots for a specific signal.
    
    Returns all snapshots of the signal over time, allowing you to see
    what the signal said on previous dates.
    
    - **signal_id**: Signal ID to get history for
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    """
    all_signals = _get_all_signals()
    signal_ids = {s.signal_id for s in all_signals}
    
    if signal_id not in signal_ids:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    snapshots = get_signal_history(signal_id, start_date, end_date)
    
    return {
        "signal_id": signal_id,
        "total_snapshots": len(snapshots),
        "snapshots": [
            {
                "snapshot_date": str(s.snapshot_date),
                "signal": s.signal.model_dump()
            }
            for s in snapshots
        ]
    }

@router.get("/signals/history")
def get_signals_at_date_endpoint(
    date: date = Query(..., description="Date to query (YYYY-MM-DD)")
):
    """
    Get all signals as they were at a specific date (point-in-time view).
    
    Returns signals as they existed on the specified date, allowing you to
    see "what did the signals say yesterday?" or any historical date.
    
    - **date**: Date to query (YYYY-MM-DD)
    """
    signals = get_signals_at_date(date)
    
    return {
        "date": str(date),
        "total_signals": len(signals),
        "signals": [s.model_dump() for s in signals]
    }

@router.get("/signals/changes")
def get_changes_since_endpoint(
    since: date = Query(..., description="Date to compare against (YYYY-MM-DD)")
):
    """
    Get all signal changes since a specific date.
    
    Shows what changed since the specified date:
    - New signals
    - Changed direction
    - Changed confidence
    - Removed signals
    
    - **since**: Date to compare against (YYYY-MM-DD)
    """
    changes = get_changes_since(since)
    
    total_changes = (
        len(changes["new_signals"]) +
        len(changes["changed_direction"]) +
        len(changes["changed_confidence"]) +
        len(changes["removed_signals"])
    )
    
    return {
        "since_date": str(since),
        "total_changes": total_changes,
        "changes": changes
    }

@router.post("/signals/snapshot")
def create_snapshot_endpoint(
    snapshot_date: Optional[date] = Query(None, description="Date for snapshot (defaults to today)")
):
    """
    Manually create a snapshot of all current signals.
    
    Useful for testing or creating snapshots at specific times.
    Daily snapshots are created automatically, but this allows manual creation.
    
    - **snapshot_date**: Optional date for snapshot (defaults to today)
    """
    snapshots = create_daily_snapshot(snapshot_date)
    
    return {
        "message": "Snapshot created successfully",
        "snapshot_date": str(snapshot_date or date.today()),
        "count": len(snapshots),
        "signal_ids": [s.signal_id for s in snapshots]
    }

@router.post("/signals/reload")
def reload_signals_endpoint():
    """
    Force reload signals from JSON file.
    
    Useful for local development to reload signals after editing the JSON file
    without restarting the server. Hot-reload also happens automatically when
    the file modification time changes.
    """
    reloaded = reload_signals()
    return {
        "message": "Signals reloaded successfully",
        "count": len(reloaded),
        "signals": [s.signal_id for s in reloaded]
    }
