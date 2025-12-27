"""
SQLAlchemy database models.

Defines the database schema for signals, snapshots, events, watchlists, and alerts.
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, date
from .database import Base

class SignalDB(Base):
    """Signal database model."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, unique=True, index=True, nullable=False)
    version = Column(String, default="v1", nullable=False)
    market = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # Bullish, Bearish, Neutral
    confidence = Column(String, nullable=False)  # Low, Medium, High
    last_updated = Column(Date, nullable=False, index=True)
    data_asof = Column(Date, nullable=False)
    explanation = Column(Text, nullable=False)
    definition = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    key_driver = Column(Text, nullable=False)
    validity_window = Column(String, nullable=False)  # intraday, daily, weekly, structural
    decay_behavior = Column(Text, nullable=False)
    related_signal_ids = Column(JSON, default=list)  # List of signal IDs
    related_markets = Column(JSON, default=list)  # List of market names
    signal_type = Column(String, nullable=False)  # structural, tactical
    score = Column(Float, nullable=True)  # Optional score (-1 to +1)
    confidence_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SignalSnapshotDB(Base):
    """Signal snapshot database model."""
    __tablename__ = "signal_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, ForeignKey("signals.signal_id"), index=True, nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)
    signal_data = Column(JSON, nullable=False)  # Full signal data as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class RegimeDB(Base):
    """Regime database model."""
    __tablename__ = "regimes"
    
    id = Column(Integer, primary_key=True, index=True)
    regime_date = Column(Date, nullable=False, index=True, unique=True)
    regime_type = Column(String, nullable=False)  # inflationary_growth, risk_off, etc.
    description = Column(Text, nullable=False)
    usd_strength = Column(String, nullable=True)  # strong, weak, mixed
    rates_direction = Column(String, nullable=True)  # rising, falling, stable
    growth_strength = Column(String, nullable=True)  # strong, weak, mixed
    created_at = Column(DateTime, default=datetime.utcnow)

class EventDB(Base):
    """Event database model."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # cpi, nfp, fed_decision, etc.
    name = Column(String, nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    impact_markets = Column(JSON, default=list)  # List of market names
    related_signal_ids = Column(JSON, default=list)  # List of signal IDs
    created_at = Column(DateTime, default=datetime.utcnow)

class WatchlistDB(Base):
    """Watchlist database model."""
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    signal_ids = Column(JSON, default=list)  # List of signal IDs
    market_ids = Column(JSON, default=list)  # List of market names
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, default=date.today)

class AlertDB(Base):
    """Alert database model."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    alert_type = Column(String, nullable=False)  # direction_change, confidence_change, etc.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    conditions = Column(JSON, nullable=False)  # Alert conditions as JSON
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(Date, default=date.today)
    last_triggered = Column(Date, nullable=True)

class AuditLogDB(Base):
    """Audit log database model."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    change_type = Column(String, nullable=False, index=True)  # signal_created, signal_updated, etc.
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # signal, regime, etc.
    description = Column(Text, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

