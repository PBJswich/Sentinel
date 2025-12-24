from datetime import date
from typing import Optional
from fastapi import APIRouter
from .models import Signal

router = APIRouter()

def _get_all_signals():
    """Returns all mocked signals."""
    return [
        Signal(
            market="WTI Crude Oil",
            category="Technical",
            name="RSI",
            direction="Bullish",
            confidence="Medium",
            updated=date.today(),
            explanation="Selling pressure appears to be easing."
        ),
        Signal(
            market="Gold",
            category="Macro",
            name="USD Trend",
            direction="Bullish",
            confidence="High",
            updated=date.today(),
            explanation="A weakening U.S. dollar supports gold prices."
        ),
        Signal(
            market="WTI Crude Oil",
            category="Fundamental",
            name="Crude Inventories",
            direction="Bearish",
            confidence="High",
            updated=date.today(),
            explanation="Weekly inventory build exceeds seasonal average, indicating oversupply."
        ),
        Signal(
            market="Copper",
            category="Sentiment",
            name="COT Positioning",
            direction="Neutral",
            confidence="Medium",
            updated=date.today(),
            explanation="Speculative positioning near neutral levels, no extreme positioning detected."
        ),
        Signal(
            market="Brent Crude",
            category="Technical",
            name="Moving Average Crossover",
            direction="Bullish",
            confidence="Low",
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
    """
    signals = _get_all_signals()
    
    if market:
        signals = [s for s in signals if s.market == market]
    
    if category:
        signals = [s for s in signals if s.category == category]
    
    return signals
