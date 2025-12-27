from typing import Optional, List, Dict
from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException
from .models import Signal, Direction, Confidence, SignalsResponse, SignalRelationship, RelationshipType, Conflict, SignalSnapshot, Regime, Event, EventType
from .signal_loader import get_all_signals, reload_signals
from .conflict_detector import get_all_conflicts, get_conflicts_for_market
from .registry import get_signal_relationships
from .snapshot_storage import (
    create_daily_snapshot,
    get_signal_history,
    get_signals_at_date,
    get_changes_since,
    initialize_snapshots,
    save_regime,
    get_regime_history,
    get_regime_at_date,
    detect_regime_transition
)
from .regime_detector import detect_regime, get_regime_impact_on_market
from .event_registry import (
    register_event,
    get_event,
    get_all_events,
    get_events_by_date,
    get_upcoming_events,
    get_events_by_type,
    get_events_for_market,
    link_event_to_signal
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
    
    # Get current regime and its impact on this market
    current_regime = detect_regime()
    regime_impact = None
    if market_group:
        regime_impact = get_regime_impact_on_market(current_regime, market_group)
    
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
        "regime": {
            "current_regime": current_regime.regime_type.value,
            "regime_description": current_regime.description,
            "regime_impact": regime_impact
        },
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
                    },
                    "related_events": [
                        {
                            "event_id": e.event_id,
                            "event_name": e.name,
                            "event_date": str(e.date),
                            "event_type": e.event_type.value
                        }
                        for e in get_all_events()
                        if s.signal_id in e.related_signal_ids
                    ]
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

@router.get("/portfolio/summary")
def get_portfolio_summary():
    """
    Get portfolio-level summary aggregating signals across all markets.
    
    Provides:
    - Aggregation by pillar (macro/fundamental/sentiment/technical)
    - Aggregation by market group (energy/metals/ags)
    - Identification of systemic forces (USD, rates, growth) from macro signals
    - Human-readable portfolio narrative
    """
    all_signals = _get_all_signals()
    from .registry import get_market_groups
    
    # Aggregate by pillar
    by_pillar = {}
    for signal in all_signals:
        pillar = signal.category
        if pillar not in by_pillar:
            by_pillar[pillar] = []
        by_pillar[pillar].append(signal)
    
    pillar_summaries = {}
    for pillar, signals in by_pillar.items():
        direction_counts = {
            "bullish": sum(1 for s in signals if s.direction == Direction.BULLISH),
            "bearish": sum(1 for s in signals if s.direction == Direction.BEARISH),
            "neutral": sum(1 for s in signals if s.direction == Direction.NEUTRAL)
        }
        
        # Determine dominant direction
        dominant_direction = max(direction_counts.items(), key=lambda x: x[1])[0] if signals else "neutral"
        
        # Calculate average confidence (1=Low, 2=Medium, 3=High)
        confidence_values = {
            Confidence.LOW: 1,
            Confidence.MEDIUM: 2,
            Confidence.HIGH: 3
        }
        avg_confidence_num = sum(confidence_values.get(s.confidence, 1) for s in signals) / len(signals) if signals else 0
        avg_confidence = "High" if avg_confidence_num >= 2.5 else ("Medium" if avg_confidence_num >= 1.5 else "Low")
        
        pillar_summaries[pillar] = {
            "count": len(signals),
            "dominant_direction": dominant_direction,
            "direction_breakdown": direction_counts,
            "average_confidence": avg_confidence
        }
    
    # Aggregate by market group
    market_groups = get_market_groups()
    by_group = {}
    for group_name, markets in market_groups.items():
        group_signals = [s for s in all_signals if s.market in markets]
        if group_signals:
            direction_counts = {
                "bullish": sum(1 for s in group_signals if s.direction == Direction.BULLISH),
                "bearish": sum(1 for s in group_signals if s.direction == Direction.BEARISH),
                "neutral": sum(1 for s in group_signals if s.direction == Direction.NEUTRAL)
            }
            by_group[group_name] = {
                "count": len(group_signals),
                "markets": markets,
                "direction_breakdown": direction_counts
            }
    
    # Identify systemic forces from macro signals
    macro_signals = by_pillar.get("Macro", [])
    systemic_forces = {}
    
    usd_signals = [s for s in macro_signals if "USD" in s.name or "DXY" in s.name]
    if usd_signals:
        usd_directions = [s.direction for s in usd_signals]
        if Direction.BULLISH in usd_directions:
            systemic_forces["USD"] = "Strong (bullish signals)"
        elif Direction.BEARISH in usd_directions:
            systemic_forces["USD"] = "Weak (bearish signals)"
        else:
            systemic_forces["USD"] = "Mixed"
    
    rates_signals = [s for s in macro_signals if "rate" in s.name.lower() or "yield" in s.name.lower() or "10Y" in s.name]
    if rates_signals:
        rates_directions = [s.direction for s in rates_signals]
        if Direction.BULLISH in rates_directions:
            systemic_forces["Rates"] = "Rising (bullish signals)"
        elif Direction.BEARISH in rates_directions:
            systemic_forces["Rates"] = "Falling (bearish signals)"
        else:
            systemic_forces["Rates"] = "Stable"
    
    growth_signals = [s for s in macro_signals if "growth" in s.name.lower() or "copper" in s.name.lower() or "equity" in s.name.lower()]
    if growth_signals:
        growth_directions = [s.direction for s in growth_signals]
        if Direction.BULLISH in growth_directions:
            systemic_forces["Growth"] = "Strong (bullish signals)"
        elif Direction.BEARISH in growth_directions:
            systemic_forces["Growth"] = "Weak (bearish signals)"
        else:
            systemic_forces["Growth"] = "Mixed"
    
    # Generate portfolio narrative
    narrative_parts = []
    narrative_parts.append(f"Portfolio overview: {len(all_signals)} total signal(s) across {len(set(s.market for s in all_signals))} market(s).")
    
    # Pillar summary
    pillar_list = ", ".join([f"{pillar} ({summary['count']} signals, {summary['dominant_direction']})" for pillar, summary in pillar_summaries.items()])
    narrative_parts.append(f"Signals by pillar: {pillar_list}.")
    
    # Market group summary
    if by_group:
        group_list = ", ".join([f"{group} ({summary['count']} signals)" for group, summary in by_group.items()])
        narrative_parts.append(f"Signals by market group: {group_list}.")
    
    # Systemic forces
    if systemic_forces:
        forces_list = ", ".join([f"{force}: {status}" for force, status in systemic_forces.items()])
        narrative_parts.append(f"Systemic forces: {forces_list}.")
    
    narrative = " ".join(narrative_parts)
    
    return {
        "total_signals": len(all_signals),
        "total_markets": len(set(s.market for s in all_signals)),
        "by_pillar": pillar_summaries,
        "by_market_group": by_group,
        "systemic_forces": systemic_forces,
        "narrative": narrative
    }

@router.get("/regime/current")
def get_current_regime():
    """
    Get the current detected macro regime.
    
    Classifies the macro environment based on signal patterns:
    - Inflationary growth: USD weak, rates rising, growth strong
    - Risk-off: USD strong, rates falling, growth weak
    - Tightening: USD strong, rates rising, growth mixed
    - Disinflationary growth: USD mixed, rates stable, growth strong
    """
    current_regime = detect_regime()
    
    # Save to history if not already saved today
    from datetime import date
    today = date.today()
    existing_regime = get_regime_at_date(today)
    if existing_regime is None or existing_regime.regime_type != current_regime.regime_type:
        save_regime(current_regime, today)
    
    # Check for transition
    yesterday = date.today() - timedelta(days=1)
    previous_regime = get_regime_at_date(yesterday)
    transition = detect_regime_transition(current_regime, previous_regime)
    
    response = {
        "regime": current_regime.model_dump(),
        "transition": transition
    }
    
    return response

@router.get("/regime/history")
def get_regime_history_endpoint(
    start_date: Optional[date] = Query(None, description="Start date for history (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for history (YYYY-MM-DD)")
):
    """
    Get historical regime classifications.
    
    Returns regime history within the specified date range, allowing you to
    see how regimes have changed over time.
    
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    """
    regimes = get_regime_history(start_date, end_date)
    
    return {
        "total_regimes": len(regimes),
        "regimes": [r.model_dump() for r in regimes]
    }

@router.get("/daily/brief")
def get_daily_brief():
    """
    Get daily market brief summarizing key changes and intelligence.
    
    Provides:
    - Total signals across all markets
    - New signals since yesterday
    - Changed signals (direction/confidence changes)
    - Emerging conflicts
    - Regime shifts
    - Key confirmations (signals aligning)
    - Human-readable narrative
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    all_signals = _get_all_signals()
    total_signals = len(all_signals)
    total_markets = len(set(s.market for s in all_signals))
    
    # Get changes since yesterday
    changes = get_changes_since(yesterday)
    new_signals = changes["new_signals"]
    changed_direction = changes["changed_direction"]
    changed_confidence = changes["changed_confidence"]
    
    # Get emerging conflicts (conflicts detected today)
    all_conflicts = get_all_conflicts()
    # For now, we'll consider all current conflicts as "emerging" if they involve changed signals
    changed_signal_ids = {c["signal_id"] for c in changed_direction + changed_confidence}
    emerging_conflicts = [
        c for c in all_conflicts
        if any(sid in changed_signal_ids for sid in c.conflicting_signals)
    ]
    
    # Check for regime shift
    current_regime = detect_regime()
    previous_regime = get_regime_at_date(yesterday)
    regime_transition = detect_regime_transition(current_regime, previous_regime)
    
    # Detect confirmations (signals aligning in same direction)
    confirmations = []
    by_market = {}
    for signal in all_signals:
        if signal.market not in by_market:
            by_market[signal.market] = []
        by_market[signal.market].append(signal)
    
    for market, signals in by_market.items():
        if len(signals) >= 2:
            directions = [s.direction for s in signals]
            if all(d == Direction.BULLISH for d in directions):
                confirmations.append({
                    "market": market,
                    "type": "bullish_alignment",
                    "count": len(signals),
                    "description": f"All {len(signals)} signals in {market} are bullish"
                })
            elif all(d == Direction.BEARISH for d in directions):
                confirmations.append({
                    "market": market,
                    "type": "bearish_alignment",
                    "count": len(signals),
                    "description": f"All {len(signals)} signals in {market} are bearish"
                })
    
    # Generate narrative
    narrative_parts = []
    narrative_parts.append(f"Daily brief for {today}: {total_signals} signal(s) across {total_markets} market(s).")
    
    if new_signals:
        narrative_parts.append(f"🆕 {len(new_signals)} new signal(s) detected.")
    
    if changed_direction:
        narrative_parts.append(f"🔄 {len(changed_direction)} signal(s) changed direction.")
    
    if changed_confidence:
        narrative_parts.append(f"📊 {len(changed_confidence)} signal(s) changed confidence.")
    
    if emerging_conflicts:
        narrative_parts.append(f"⚠️ {len(emerging_conflicts)} emerging conflict(s) detected.")
    
    if regime_transition:
        narrative_parts.append(f"🌍 Regime shift: {regime_transition['description']}")
    
    if confirmations:
        narrative_parts.append(f"✅ {len(confirmations)} market(s) showing signal alignment.")
    
    narrative = " ".join(narrative_parts)
    
    return {
        "date": str(today),
        "total_signals": total_signals,
        "total_markets": total_markets,
        "new_signals": new_signals,
        "new_signals_count": len(new_signals),
        "changed_direction": changed_direction,
        "changed_direction_count": len(changed_direction),
        "changed_confidence": changed_confidence,
        "changed_confidence_count": len(changed_confidence),
        "emerging_conflicts": [c.model_dump() for c in emerging_conflicts],
        "emerging_conflicts_count": len(emerging_conflicts),
        "regime_transition": regime_transition,
        "current_regime": current_regime.model_dump(),
        "confirmations": confirmations,
        "confirmations_count": len(confirmations),
        "narrative": narrative
    }

@router.get("/events")
def get_events(
    event_type: Optional[str] = Query(None, description="Filter by event type (cpi, nfp, fed_decision, etc.)"),
    market: Optional[str] = Query(None, description="Filter by impacted market"),
    upcoming_days: Optional[int] = Query(None, ge=1, description="Get upcoming events within N days")
):
    """
    Get all registered events.
    
    - **event_type**: Optional filter by event type (case-insensitive)
    - **market**: Optional filter by impacted market
    - **upcoming_days**: Optional filter for upcoming events within N days
    """
    events = get_all_events()
    
    if event_type:
        try:
            event_type_enum = EventType[event_type.upper()]
            events = [e for e in events if e.event_type == event_type_enum]
        except KeyError:
            events = []
    
    if market:
        events = [e for e in events if market in e.impact_markets]
    
    if upcoming_days:
        upcoming = get_upcoming_events(upcoming_days)
        if event_type or market:
            # Re-apply filters
            if event_type:
                try:
                    event_type_enum = EventType[event_type.upper()]
                    upcoming = [e for e in upcoming if e.event_type == event_type_enum]
                except KeyError:
                    upcoming = []
            if market:
                upcoming = [e for e in upcoming if market in e.impact_markets]
        events = upcoming
    
    return {
        "total_events": len(events),
        "events": [e.model_dump() for e in events]
    }

@router.get("/events/{event_id}")
def get_event_endpoint(event_id: str):
    """
    Get a specific event by ID.
    
    - **event_id**: Event ID
    """
    event = get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    return {
        "event": event.model_dump()
    }

@router.get("/events/{event_id}/impact")
def get_event_impact(event_id: str):
    """
    Get impact analysis for a specific event.
    
    Shows:
    - Event details
    - Related signals
    - Impacted markets
    - Signal changes around event date
    
    - **event_id**: Event ID
    """
    event = get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    # Get related signals
    all_signals = _get_all_signals()
    related_signals = [s for s in all_signals if s.signal_id in event.related_signal_ids]
    
    # Get signals for impacted markets
    impacted_market_signals = [s for s in all_signals if s.market in event.impact_markets]
    
    # Get changes around event date (within 3 days)
    event_date = event.event_date
    changes_before = get_changes_since(event_date - timedelta(days=3))
    changes_after = get_changes_since(event_date)
    
    return {
        "event": event.model_dump(),
        "related_signals": [s.model_dump() for s in related_signals],
        "related_signals_count": len(related_signals),
        "impacted_markets": event.impact_markets,
        "impacted_market_signals": [s.model_dump() for s in impacted_market_signals],
        "impacted_market_signals_count": len(impacted_market_signals),
        "changes_around_event": {
            "before_event": {
                "date_range": f"{event_date - timedelta(days=3)} to {event_date}",
                "changes": changes_before
            },
            "after_event": {
                "date_range": f"{event_date} to {date.today()}",
                "changes": changes_after
            }
        }
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
