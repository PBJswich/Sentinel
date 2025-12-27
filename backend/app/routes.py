from typing import Optional, List, Dict
from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from .models import (
    Signal, Direction, Confidence, SignalsResponse, SignalRelationship, RelationshipType,
    Conflict, SignalSnapshot, Regime, Event, EventType, Watchlist, Alert, AlertType,
    ValidityWindow, SignalType
)
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
from .watchlist_storage import (
    create_watchlist,
    get_watchlist,
    get_all_watchlists,
    update_watchlist,
    delete_watchlist
)
from .alert_storage import (
    create_alert,
    get_alert,
    get_all_alerts,
    update_alert,
    delete_alert,
    evaluate_all_alerts
)
from .scoring import calculate_signal_score, get_score_breakdown
from .audit_log import log_change, get_audit_log, get_changes_for_entity, ChangeType
from .system_health import check_system_health, check_data_quality
from .database import get_db
from .db_service import save_signal as save_signal_db, get_all_signals_db, get_signal_by_id_db
from .cache import cache_result, clear_cache, get_cache_stats

router = APIRouter()

# Initialize snapshots on module load
initialize_snapshots()

def _get_all_signals():
    """Returns all signals loaded from JSON file with hot-reload support."""
    return get_all_signals()

def _filter_signals(
    signals: list[Signal],
    market: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    confidence: Optional[str] = None,
    validity_window: Optional[str] = None,
    signal_type: Optional[str] = None,
    freshness: Optional[str] = None,
    search: Optional[str] = None
) -> list[Signal]:
    """Filter signals by various criteria (case-insensitive)."""
    filtered = signals
    
    if market:
        market_lower = market.lower().strip()
        filtered = [s for s in filtered if s.market.lower() == market_lower]
    
    if category:
        category_lower = category.lower().strip()
        filtered = [s for s in filtered if s.category.lower() == category_lower]
    
    if direction:
        try:
            direction_enum = Direction[direction.upper()]
            filtered = [s for s in filtered if s.direction == direction_enum]
        except KeyError:
            filtered = []
    
    if confidence:
        try:
            confidence_enum = Confidence[confidence.upper()]
            filtered = [s for s in filtered if s.confidence == confidence_enum]
        except KeyError:
            filtered = []
    
    if validity_window:
        try:
            window_enum = ValidityWindow[validity_window.upper()]
            filtered = [s for s in filtered if s.validity_window == window_enum]
        except KeyError:
            filtered = []
    
    if signal_type:
        try:
            type_enum = SignalType[signal_type.upper()]
            filtered = [s for s in filtered if s.signal_type == type_enum]
        except KeyError:
            filtered = []
    
    if freshness:
        if freshness.lower() == "fresh":
            filtered = [s for s in filtered if s.data_freshness.value == "fresh"]
        elif freshness.lower() == "stale":
            filtered = [s for s in filtered if s.data_freshness.value == "stale"]
        elif freshness.lower() == "unknown":
            filtered = [s for s in filtered if s.data_freshness.value == "unknown"]
    
    if search:
        search_lower = search.lower().strip()
        filtered = [
            s for s in filtered
            if search_lower in s.explanation.lower()
            or search_lower in s.definition.lower()
            or search_lower in s.name.lower()
            or search_lower in s.market.lower()
        ]
    
    return filtered

def _sort_signals(signals: list[Signal], sort_by: Optional[str] = None) -> list[Signal]:
    """Sort signals by specified criteria."""
    if not sort_by:
        return signals
    
    sort_lower = sort_by.lower()
    
    if sort_lower == "confidence":
        # Sort by confidence (High > Medium > Low)
        confidence_order = {Confidence.HIGH: 3, Confidence.MEDIUM: 2, Confidence.LOW: 1}
        return sorted(signals, key=lambda s: confidence_order.get(s.confidence, 0), reverse=True)
    elif sort_lower == "date" or sort_lower == "last_updated":
        return sorted(signals, key=lambda s: s.last_updated, reverse=True)
    elif sort_lower == "market":
        return sorted(signals, key=lambda s: s.market.lower())
    elif sort_lower == "age":
        return sorted(signals, key=lambda s: s.age_days, reverse=True)
    else:
        return signals

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
    direction: Optional[str] = Query(None, description="Filter by direction (bullish/bearish/neutral)"),
    confidence: Optional[str] = Query(None, description="Filter by confidence (low/medium/high)"),
    validity_window: Optional[str] = Query(None, description="Filter by validity window (intraday/daily/weekly/structural)"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (structural/tactical)"),
    freshness: Optional[str] = Query(None, description="Filter by freshness (fresh/stale/unknown)"),
    search: Optional[str] = Query(None, description="Full-text search in explanation, definition, name, market"),
    sort_by: Optional[str] = Query(None, description="Sort by (confidence/date/market/age)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of signals to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of signals to skip")
):
    """
    Get signals with optional filtering, searching, and sorting.
    
    - **market**: Filter by market name (case-insensitive)
    - **category**: Filter by category (case-insensitive)
    - **direction**: Filter by direction (bullish/bearish/neutral)
    - **confidence**: Filter by confidence (low/medium/high)
    - **validity_window**: Filter by validity window (intraday/daily/weekly/structural)
    - **signal_type**: Filter by signal type (structural/tactical)
    - **freshness**: Filter by freshness (fresh/stale/unknown)
    - **search**: Full-text search in explanation, definition, name, market
    - **sort_by**: Sort by (confidence/date/market/age)
    - **limit**: Maximum number of signals to return (pagination)
    - **offset**: Number of signals to skip (pagination)
    
    Returns empty signals list if no signals match the filters.
    """
    all_signals = _get_all_signals()
    total = len(all_signals)
    
    # Apply filters
    filtered_signals = _filter_signals(
        all_signals,
        market=market,
        category=category,
        direction=direction,
        confidence=confidence,
        validity_window=validity_window,
        signal_type=signal_type,
        freshness=freshness,
        search=search
    )
    filtered_count = len(filtered_signals)
    
    # Apply sorting
    filtered_signals = _sort_signals(filtered_signals, sort_by)
    
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
    direction: Optional[str] = Query(None, description="Filter by direction (bullish/bearish/neutral)"),
    confidence: Optional[str] = Query(None, description="Filter by confidence (low/medium/high)"),
    sort_by: Optional[str] = Query(None, description="Sort by (confidence/date/age)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of signals to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of signals to skip")
):
    """
    Get signals for a specific market with optional filtering and sorting.
    
    - **market**: Market name (case-insensitive, e.g., "wti crude oil", "Gold")
    - **category**: Optional category filter (case-insensitive)
    - **direction**: Filter by direction (bullish/bearish/neutral)
    - **confidence**: Filter by confidence (low/medium/high)
    - **sort_by**: Sort by (confidence/date/age)
    - **limit**: Maximum number of signals to return (pagination)
    - **offset**: Number of signals to skip (pagination)
    
    Returns empty signals list if market not found or no signals match.
    """
    all_signals = _get_all_signals()
    total = len(all_signals)
    
    # Filter by market (case-insensitive) and optional filters
    filtered_signals = _filter_signals(
        all_signals,
        market=market,
        category=category,
        direction=direction,
        confidence=confidence
    )
    filtered_count = len(filtered_signals)
    
    # Apply sorting
    filtered_signals = _sort_signals(filtered_signals, sort_by)
    
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
                    "score": s.score if s.score is not None else calculate_signal_score(s),
                    "score_breakdown": get_score_breakdown(s),
                    "confidence_rationale": s.confidence_rationale,
                    "why_this_signal": f"{s.key_driver}. {s.explanation}",
                    "related_events": [
                        {
                            "event_id": e.event_id,
                            "event_name": e.name,
                            "event_date": str(e.event_date),
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

@router.get("/watchlists")
def get_watchlists():
    """Get all watchlists."""
    watchlists = get_all_watchlists()
    return {
        "total_watchlists": len(watchlists),
        "watchlists": [w.model_dump() for w in watchlists]
    }

@router.get("/watchlists/{watchlist_id}")
def get_watchlist_endpoint(watchlist_id: str):
    """Get a specific watchlist by ID."""
    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail=f"Watchlist {watchlist_id} not found")
    return {"watchlist": watchlist.model_dump()}

@router.get("/watchlists/{watchlist_id}/signals")
def get_watchlist_signals(watchlist_id: str):
    """Get signals for a specific watchlist."""
    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail=f"Watchlist {watchlist_id} not found")
    
    all_signals = _get_all_signals()
    signal_map = {s.signal_id: s for s in all_signals}
    
    # Get signals by ID
    signals_by_id = [signal_map[sid] for sid in watchlist.signal_ids if sid in signal_map]
    
    # Get signals by market
    signals_by_market = [s for s in all_signals if s.market in watchlist.market_ids]
    
    # Combine and deduplicate
    all_watchlist_signals = {s.signal_id: s for s in signals_by_id + signals_by_market}
    
    return {
        "watchlist_id": watchlist_id,
        "watchlist_name": watchlist.name,
        "total_signals": len(all_watchlist_signals),
        "signals": [s.model_dump() for s in all_watchlist_signals.values()]
    }

@router.post("/watchlists")
def create_watchlist_endpoint(watchlist: Watchlist):
    """Create a new watchlist."""
    created = create_watchlist(watchlist)
    return {
        "message": "Watchlist created successfully",
        "watchlist": created.model_dump()
    }

@router.put("/watchlists/{watchlist_id}")
def update_watchlist_endpoint(watchlist_id: str, watchlist: Watchlist):
    """Update an existing watchlist."""
    if watchlist_id != watchlist.watchlist_id:
        raise HTTPException(status_code=400, detail="watchlist_id in path must match watchlist_id in body")
    
    updated = update_watchlist(watchlist_id, watchlist)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Watchlist {watchlist_id} not found")
    
    return {
        "message": "Watchlist updated successfully",
        "watchlist": updated.model_dump()
    }

@router.delete("/watchlists/{watchlist_id}")
def delete_watchlist_endpoint(watchlist_id: str):
    """Delete a watchlist."""
    deleted = delete_watchlist(watchlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Watchlist {watchlist_id} not found")
    
    return {
        "message": "Watchlist deleted successfully",
        "watchlist_id": watchlist_id
    }

@router.get("/alerts")
def get_alerts():
    """Get all alerts."""
    alerts = get_all_alerts()
    return {
        "total_alerts": len(alerts),
        "alerts": [a.model_dump() for a in alerts]
    }

@router.get("/alerts/{alert_id}")
def get_alert_endpoint(alert_id: str):
    """Get a specific alert by ID."""
    alert = get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"alert": alert.model_dump()}

@router.get("/alerts/active")
def get_active_alerts():
    """Evaluate all alerts and return currently triggered ones."""
    triggered = evaluate_all_alerts()
    return {
        "total_triggered": len(triggered),
        "triggered_alerts": triggered
    }

@router.post("/alerts")
def create_alert_endpoint(alert: Alert):
    """Create a new alert."""
    created = create_alert(alert)
    return {
        "message": "Alert created successfully",
        "alert": created.model_dump()
    }

@router.put("/alerts/{alert_id}")
def update_alert_endpoint(alert_id: str, alert: Alert):
    """Update an existing alert."""
    if alert_id != alert.alert_id:
        raise HTTPException(status_code=400, detail="alert_id in path must match alert_id in body")
    
    updated = update_alert(alert_id, alert)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return {
        "message": "Alert updated successfully",
        "alert": updated.model_dump()
    }

@router.delete("/alerts/{alert_id}")
def delete_alert_endpoint(alert_id: str):
    """Delete an alert."""
    deleted = delete_alert(alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return {
        "message": "Alert deleted successfully",
        "alert_id": alert_id
    }

@router.get("/signals/{signal_id}/score")
def get_signal_score_endpoint(signal_id: str, include_breakdown: bool = Query(True, description="Include score breakdown")):
    """
    Get score and breakdown for a specific signal.
    
    - **signal_id**: Signal ID
    - **include_breakdown**: Whether to include detailed score breakdown
    """
    all_signals = _get_all_signals()
    signal_map = {s.signal_id: s for s in all_signals}
    
    if signal_id not in signal_map:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    signal = signal_map[signal_id]
    score = signal.score if signal.score is not None else calculate_signal_score(signal)
    
    response = {
        "signal_id": signal_id,
        "signal_name": signal.name,
        "score": round(score, 3)
    }
    
    if include_breakdown:
        response["breakdown"] = get_score_breakdown(signal)
    
    return response

@router.get("/signals/definitions")
def get_signal_definitions():
    """
    Get signal definition library with all signal definitions, sources, and logic.
    
    Provides a comprehensive library of all signal definitions for reference.
    """
    all_signals = _get_all_signals()
    
    # Group by category
    by_category = {}
    for signal in all_signals:
        category = signal.category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append({
            "signal_id": signal.signal_id,
            "name": signal.name,
            "market": signal.market,
            "definition": signal.definition,
            "source": signal.source,
            "validity_window": signal.validity_window.value,
            "signal_type": signal.signal_type.value,
            "decay_behavior": signal.decay_behavior,
            "confidence_rationale": signal.confidence_rationale
        })
    
    return {
        "total_signals": len(all_signals),
        "by_category": by_category,
        "note": "This library provides definitions and logic for all signals. Scores are optional and never replace explanations."
    }

@router.get("/audit/log")
def get_audit_log_endpoint(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (signal, regime, etc.)"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)")
):
    """
    Get audit log of all changes.
    
    Provides full traceability of what changed, when, and why.
    
    - **entity_id**: Filter by entity ID
    - **entity_type**: Filter by entity type
    - **change_type**: Filter by change type
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    """
    change_type_enum = None
    if change_type:
        try:
            change_type_enum = ChangeType[change_type.upper()]
        except KeyError:
            pass
    
    log_entries = get_audit_log(
        entity_id=entity_id,
        entity_type=entity_type,
        change_type=change_type_enum,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "total_entries": len(log_entries),
        "entries": log_entries
    }

@router.get("/audit/log/{entity_type}/{entity_id}")
def get_entity_audit_log(entity_type: str, entity_id: str):
    """
    Get audit log for a specific entity.
    
    - **entity_type**: Entity type (signal, regime, etc.)
    - **entity_id**: Entity ID
    """
    entries = get_changes_for_entity(entity_id, entity_type)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total_changes": len(entries),
        "changes": entries
    }

@router.get("/health")
def get_system_health():
    """
    Get system health status and metrics.
    
    Provides:
    - Overall health status
    - System metrics
    - Data quality checks
    - Warnings
    """
    health = check_system_health()
    return health

@router.get("/health/quality")
def get_data_quality():
    """
    Get data quality validation results.
    
    Validates:
    - No signal without explanation
    - No hidden weighting
    - No silent data substitution
    - Conflicts are visible
    """
    quality = check_data_quality()
    return quality

@router.post("/signals")
def create_signal_endpoint(signal: Signal, db: Session = Depends(get_db)):
    """
    Create a new signal.
    
    - **signal**: Signal data
    """
    # Save to database
    db_signal = save_signal_db(db, signal)
    
    # Log the creation
    log_change(
        change_type=ChangeType.SIGNAL_CREATED,
        entity_id=signal.signal_id,
        entity_type="signal",
        description=f"Signal {signal.signal_id} created",
        new_value=signal.model_dump()
    )
    
    # Clear cache
    clear_cache("get_all_signals")
    
    return {
        "message": "Signal created successfully",
        "signal": signal.model_dump()
    }

@router.put("/signals/{signal_id}")
def update_signal_endpoint(signal_id: str, signal: Signal, db: Session = Depends(get_db)):
    """
    Update an existing signal.
    
    - **signal_id**: Signal ID
    - **signal**: Updated signal data
    """
    if signal_id != signal.signal_id:
        raise HTTPException(status_code=400, detail="signal_id in path must match signal_id in body")
    
    # Get old value for audit log
    old_signal = get_signal_by_id_db(db, signal_id)
    old_value = old_signal.model_dump() if old_signal else None
    
    # Save to database
    db_signal = save_signal_db(db, signal)
    
    # Log the update
    log_change(
        change_type=ChangeType.SIGNAL_UPDATED,
        entity_id=signal.signal_id,
        entity_type="signal",
        description=f"Signal {signal.signal_id} updated",
        old_value=old_value,
        new_value=signal.model_dump()
    )
    
    # Clear cache
    clear_cache("get_all_signals")
    
    return {
        "message": "Signal updated successfully",
        "signal": signal.model_dump()
    }

@router.delete("/signals/{signal_id}")
def delete_signal_endpoint(signal_id: str, db: Session = Depends(get_db)):
    """
    Delete a signal.
    
    - **signal_id**: Signal ID
    """
    from .db_models import SignalDB
    
    db_signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not db_signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    # Get old value for audit log
    old_value = {
        "signal_id": db_signal.signal_id,
        "name": db_signal.name,
        "market": db_signal.market
    }
    
    # Delete from database
    db.delete(db_signal)
    db.commit()
    
    # Log the deletion
    log_change(
        change_type=ChangeType.SIGNAL_DELETED,
        entity_id=signal_id,
        entity_type="signal",
        description=f"Signal {signal_id} deleted",
        old_value=old_value
    )
    
    # Clear cache
    clear_cache("get_all_signals")
    
    return {
        "message": "Signal deleted successfully",
        "signal_id": signal_id
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
    
    # Log the reload
    for signal in reloaded:
        log_change(
            change_type=ChangeType.SIGNAL_UPDATED,
            entity_id=signal.signal_id,
            entity_type="signal",
            description=f"Signal reloaded from JSON file"
        )
    
    # Clear cache
    clear_cache()
    
    return {
        "message": "Signals reloaded successfully",
        "count": len(reloaded),
        "signals": [s.signal_id for s in reloaded]
    }

@router.get("/cache/stats")
def get_cache_stats_endpoint():
    """Get cache statistics."""
    return get_cache_stats()

@router.post("/cache/clear")
def clear_cache_endpoint(pattern: Optional[str] = Query(None, description="Optional pattern to match cache keys")):
    """Clear cache entries."""
    clear_cache(pattern)
    return {
        "message": "Cache cleared successfully",
        "pattern": pattern
    }
