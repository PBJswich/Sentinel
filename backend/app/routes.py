from datetime import date
from typing import Optional
from fastapi import APIRouter
from .models import Signal, Direction, Confidence

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

@router.get("/signals", response_model=list[Signal])
def get_signals(
    market: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Get signals with optional filtering by market and/or category.
    
    - **market**: Filter by market name (e.g., "WTI Crude Oil", "Gold")
    - **category**: Filter by category (e.g., "Technical", "Macro", "Fundamental", "Sentiment")
    
    Returns empty list if no signals match the filters.
    """
    signals = _get_all_signals()
    
    if market:
        signals = [s for s in signals if s.market == market]
    
    if category:
        signals = [s for s in signals if s.category == category]
    
    return signals

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
