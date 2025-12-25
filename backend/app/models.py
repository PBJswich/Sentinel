from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import date

class Direction(str, Enum):
    """Allowed values for signal direction."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"

class Confidence(str, Enum):
    """Allowed values for signal confidence."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Signal(BaseModel):
    market: str
    category: str
    name: str
    direction: Direction
    confidence: Confidence
    updated: date
    explanation: str = Field(..., min_length=10, description="Clear explanation (1-2 sentences)")
    
    @field_validator('explanation')
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        """Ensure explanation is clear and meaningful."""
        if not v or not v.strip():
            raise ValueError("Explanation cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Explanation must be at least 10 characters long")
        # Check for sentence structure (rough heuristic: contains period or is substantial)
        if len(v.strip()) < 20 and '.' not in v:
            raise ValueError("Explanation should be a clear sentence (1-2 sentences)")
        return v.strip()
