from datetime import date
from typing import Optional
from fastapi import APIRouter, Query
from .models import Signal, Direction, Confidence, SignalsResponse

router = APIRouter()

def _get_all_signals():
    """Returns all mocked signals."""
    return [
        Signal(
            market="WTI Crude Oil",
            category="Technical",
            name="RSI",
            direction=Direction.BULLISH,
            confidence=Confidence.MEDIUM,
            updated=date.today(),
            explanation="Selling pressure appears to be easing."
        ),
        Signal(
            market="Gold",
            category="Macro",
            name="USD Trend",
            direction=Direction.BULLISH,
            confidence=Confidence.HIGH,
            updated=date.today(),
            explanation="A weakening U.S. dollar supports gold prices."
        ),
        Signal(
            market="WTI Crude Oil",
            category="Fundamental",
            name="Crude Inventories",
            direction=Direction.BEARISH,
            confidence=Confidence.HIGH,
            updated=date.today(),
            explanation="Weekly inventory build exceeds seasonal average, indicating oversupply."
        ),
        Signal(
            market="Copper",
            category="Sentiment",
            name="COT Positioning",
            direction=Direction.NEUTRAL,
            confidence=Confidence.MEDIUM,
            updated=date.today(),
            explanation="Speculative positioning near neutral levels, no extreme positioning detected."
        ),
        Signal(
            market="Brent Crude",
            category="Technical",
            name="Moving Average Crossover",
            direction=Direction.BULLISH,
            confidence=Confidence.LOW,
            updated=date.today(),
            explanation="20-day MA crossed above 100-day MA, but momentum remains weak."
        ),
    ]

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
