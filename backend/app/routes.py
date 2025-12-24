from datetime import date
from fastapi import APIRouter
from .models import Signal

router = APIRouter()

@router.get("/signals", response_model=list[Signal])
def get_signals():
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
    ]
