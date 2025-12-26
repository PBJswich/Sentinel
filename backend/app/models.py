from enum import Enum
from pydantic import BaseModel, Field, field_validator, computed_field
from datetime import date, timedelta
from typing import List, Optional

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

class DataFreshness(str, Enum):
    """Data freshness status flags."""
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"

class Signal(BaseModel):
    signal_id: str = Field(..., description="Stable unique identifier for this signal")
    version: str = Field(default="v1", description="Signal version (e.g., v1, v2)")
    market: str
    category: str
    name: str
    direction: Direction
    confidence: Confidence
    last_updated: date = Field(..., description="When this signal was last updated/refreshed")
    data_asof: date = Field(..., description="The date the underlying data is from (may differ from last_updated)")
    explanation: str = Field(..., min_length=10, description="Clear explanation (1-2 sentences)")
    definition: str = Field(..., description="Definition of what this signal measures")
    source: str = Field(..., description="Data source (e.g., 'price data', 'inventory report', 'news analysis')")
    
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
    
    @computed_field
    @property
    def data_freshness(self) -> DataFreshness:
        """
        Calculate data freshness based on data_asof date.
        - fresh: data is less than 2 days old
        - stale: data is 2+ days old
        - unknown: if dates are invalid or missing
        """
        try:
            today = date.today()
            days_old = (today - self.data_asof).days
            
            if days_old < 0:
                return DataFreshness.UNKNOWN
            elif days_old < 2:
                return DataFreshness.FRESH
            else:
                return DataFreshness.STALE
        except (ValueError, TypeError):
            return DataFreshness.UNKNOWN

class SignalsResponse(BaseModel):
    """Response model with signals and metadata."""
    signals: List[Signal]
    total: int = Field(..., description="Total number of signals available")
    filtered_count: int = Field(..., description="Number of signals after filtering")
    limit: Optional[int] = Field(None, description="Pagination limit applied")
    offset: Optional[int] = Field(None, description="Pagination offset applied")
