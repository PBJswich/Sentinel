from pydantic import BaseModel
from datetime import date

class Signal(BaseModel):
    market: str
    category: str
    name: str
    direction: str  # Bullish / Bearish / Neutral
    confidence: str  # Low / Medium / High
    updated: date
    explanation: str
