from typing import Optional
from fastapi import APIRouter, Query
from .models import Signal, Direction, Confidence, SignalsResponse
from .signal_loader import get_all_signals, reload_signals

router = APIRouter()

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
    
    return SignalsResponse(
        signals=filtered_signals,
        total=total,
        filtered_count=filtered_count,
        limit=limit,
        offset=offset
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
    
    return SignalsResponse(
        signals=filtered_signals,
        total=total,
        filtered_count=filtered_count,
        limit=limit,
        offset=offset
    )

@router.get("/markets")
def get_markets():
    """
    Get list of unique markets that have signals.
    
    Returns a list of market names sorted alphabetically.
    """
    signals = _get_all_signals()
    markets = sorted(set(s.market for s in signals))
    return {"markets": markets}

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
    Get the signal registry with all registered signal IDs and metadata.
    
    Returns the internal signal registry showing stable identifiers, versions,
    and basic metadata for all available signals.
    """
    from .registry import get_registry, list_all_signal_ids
    
    registry = get_registry()
    signal_ids = list_all_signal_ids()
    
    return {
        "registry_version": "v1",
        "total_signals": len(signal_ids),
        "signal_ids": signal_ids,
        "signals": registry
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
        
        market_summaries.append({
            "market": market_name,
            "total_signals": len(signals),
            "direction_breakdown": {
                "bullish": bullish,
                "bearish": bearish,
                "neutral": neutral
            },
            "high_confidence_count": high_conf,
            "signals": [
                {
                    "name": s.name,
                    "category": s.category,
                    "direction": s.direction.value,
                    "confidence": s.confidence.value,
                    "definition": s.definition,
                    "source": s.source,
                    "explanation": s.explanation,
                    "signal_id": s.signal_id,
                    "version": s.version,
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
        "markets": market_summaries,
        "categories": category_summaries,
        "data_freshness_summary": {
            "most_recent_update": str(max(s.last_updated for s in filtered_signals)),
            "oldest_data": str(min(s.data_asof for s in filtered_signals)),
            "fresh_count": sum(1 for s in filtered_signals if s.data_freshness.value == "fresh"),
            "stale_count": sum(1 for s in filtered_signals if s.data_freshness.value == "stale"),
            "unknown_count": sum(1 for s in filtered_signals if s.data_freshness.value == "unknown")
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
