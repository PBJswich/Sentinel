from enum import Enum
from pydantic import BaseModel, Field, field_validator, computed_field
from datetime import date, timedelta
from typing import List, Optional, Dict

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

class ValidityWindow(str, Enum):
    """Expected signal lifespan."""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    STRUCTURAL = "structural"

class SignalType(str, Enum):
    """Signal type classification."""
    STRUCTURAL = "structural"
    TACTICAL = "tactical"

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
    key_driver: str = Field(..., description="Rationale/why this signal matters (key driver)")
    validity_window: ValidityWindow = Field(..., description="Expected signal lifespan")
    decay_behavior: str = Field(..., description="Description of how signal loses relevance over time")
    related_signal_ids: List[str] = Field(default_factory=list, description="List of related signal IDs")
    related_markets: List[str] = Field(default_factory=list, description="List of markets this signal impacts")
    signal_type: SignalType = Field(..., description="Signal type: structural or tactical")
    
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
    
    @computed_field
    @property
    def age_days(self) -> int:
        """
        Calculate signal age in days based on last_updated date.
        Returns number of days since signal was last updated.
        """
        try:
            today = date.today()
            return (today - self.last_updated).days
        except (ValueError, TypeError):
            return 0
    
    @computed_field
    @property
    def is_stale(self) -> bool:
        """
        Determine if signal is stale based on validity_window and age.
        
        Staleness thresholds:
        - intraday: > 1 day old
        - daily: > 2 days old
        - weekly: > 8 days old
        - structural: > 30 days old
        """
        age = self.age_days
        
        if self.validity_window == ValidityWindow.INTRADAY:
            return age > 1
        elif self.validity_window == ValidityWindow.DAILY:
            return age > 2
        elif self.validity_window == ValidityWindow.WEEKLY:
            return age > 8
        elif self.validity_window == ValidityWindow.STRUCTURAL:
            return age > 30
        else:
            return age > 7  # Default threshold

class SignalsResponse(BaseModel):
    """Response model with signals and metadata."""
    signals: List[Signal]
    total: int = Field(..., description="Total number of signals available")
    filtered_count: int = Field(..., description="Number of signals after filtering")
    limit: Optional[int] = Field(None, description="Pagination limit applied")
    offset: Optional[int] = Field(None, description="Pagination offset applied")
    stale_warnings: Optional[List[Dict]] = Field(None, description="Warnings for stale signals")

class RelationshipType(str, Enum):
    """Types of signal relationships."""
    CONFIRMS = "confirms"
    CONTRADICTS = "contradicts"
    RELATED = "related"

class SignalRelationship(BaseModel):
    """Relationship between signals."""
    signal_id: str = Field(..., description="Signal ID this relationship refers to")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    description: Optional[str] = Field(None, description="Optional description of the relationship")

class ConflictType(str, Enum):
    """Types of signal conflicts."""
    OPPOSITE_DIRECTION = "opposite_direction"
    STRUCTURAL_TACTICAL_MISMATCH = "structural_tactical_mismatch"
    TIMEFRAME_MISMATCH = "timeframe_mismatch"

class Conflict(BaseModel):
    """Conflict between signals."""
    conflicting_signals: List[str] = Field(..., description="List of signal IDs in conflict")
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    description: str = Field(..., description="Human-readable description of the conflict")
    market: Optional[str] = Field(None, description="Market where conflict occurs (if applicable)")
    timeframe_mismatch: Optional[str] = Field(None, description="Description of timeframe mismatch if applicable")
    structural_vs_transient: Optional[str] = Field(None, description="Description of structural vs transient tension if applicable")

class SignalSnapshot(BaseModel):
    """Historical snapshot of a signal at a point in time."""
    signal_id: str = Field(..., description="Signal ID")
    snapshot_date: date = Field(..., description="Date of this snapshot")
    signal: Signal = Field(..., description="Full signal data at this point in time")

class RegimeType(str, Enum):
    """Types of macro regimes."""
    INFLATIONARY_GROWTH = "inflationary_growth"
    RISK_OFF = "risk_off"
    TIGHTENING = "tightening"
    DISINFLATIONARY_GROWTH = "disinflationary_growth"
    UNCERTAIN = "uncertain"

class Regime(BaseModel):
    """Macro regime classification."""
    regime_type: RegimeType = Field(..., description="Type of regime")
    description: str = Field(..., description="Human-readable description of the regime")
    indicators: Dict[str, str] = Field(..., description="Key indicators that led to this classification")
    impact: Dict[str, str] = Field(..., description="Expected impact on commodities by market group")
    detected_date: date = Field(..., description="Date this regime was detected")
    confidence: str = Field(..., description="Confidence level in regime classification (High/Medium/Low)")

class EventType(str, Enum):
    """Types of macro events."""
    CPI = "cpi"
    NFP = "nfp"
    FED_DECISION = "fed_decision"
    INVENTORY_REPORT = "inventory_report"
    OTHER = "other"

class Event(BaseModel):
    """Macro event that impacts markets."""
    event_id: str = Field(..., description="Unique identifier for the event")
    event_type: EventType = Field(..., description="Type of event")
    name: str = Field(..., description="Event name (e.g., 'CPI Release', 'NFP Report')")
    event_date: date = Field(..., description="Date of the event")
    description: str = Field(..., description="Description of the event")
    impact_markets: List[str] = Field(default_factory=list, description="Markets impacted by this event")
    related_signal_ids: List[str] = Field(default_factory=list, description="Signal IDs related to this event")
