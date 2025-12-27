"""
Database service layer.

Provides functions to interact with the database for signals, snapshots, events, etc.
"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .db_models import (
    SignalDB, SignalSnapshotDB, RegimeDB, EventDB, 
    WatchlistDB, AlertDB, AuditLogDB
)
from .models import Signal, SignalSnapshot, Regime, Event, Watchlist, Alert
from .scoring import calculate_signal_score

def signal_to_db(signal: Signal) -> SignalDB:
    """Convert Signal model to SignalDB."""
    return SignalDB(
        signal_id=signal.signal_id,
        version=signal.version,
        market=signal.market,
        category=signal.category,
        name=signal.name,
        direction=signal.direction.value,
        confidence=signal.confidence.value,
        last_updated=signal.last_updated,
        data_asof=signal.data_asof,
        explanation=signal.explanation,
        definition=signal.definition,
        source=signal.source,
        key_driver=signal.key_driver,
        validity_window=signal.validity_window.value,
        decay_behavior=signal.decay_behavior,
        related_signal_ids=signal.related_signal_ids,
        related_markets=signal.related_markets,
        signal_type=signal.signal_type.value,
        score=signal.score if signal.score is not None else calculate_signal_score(signal),
        confidence_rationale=signal.confidence_rationale
    )

def db_to_signal(db_signal: SignalDB) -> Signal:
    """Convert SignalDB to Signal model."""
    from .models import Direction, Confidence, ValidityWindow, SignalType
    
    return Signal(
        signal_id=db_signal.signal_id,
        version=db_signal.version,
        market=db_signal.market,
        category=db_signal.category,
        name=db_signal.name,
        direction=Direction[db_signal.direction.upper()],
        confidence=Confidence[db_signal.confidence.upper()],
        last_updated=db_signal.last_updated,
        data_asof=db_signal.data_asof,
        explanation=db_signal.explanation,
        definition=db_signal.definition,
        source=db_signal.source,
        key_driver=db_signal.key_driver,
        validity_window=ValidityWindow[db_signal.validity_window.upper()],
        decay_behavior=db_signal.decay_behavior,
        related_signal_ids=db_signal.related_signal_ids or [],
        related_markets=db_signal.related_markets or [],
        signal_type=SignalType[db_signal.signal_type.upper()],
        score=db_signal.score,
        confidence_rationale=db_signal.confidence_rationale
    )

def save_signal(db: Session, signal: Signal) -> SignalDB:
    """Save or update a signal in the database."""
    db_signal = db.query(SignalDB).filter(SignalDB.signal_id == signal.signal_id).first()
    
    if db_signal:
        # Update existing
        db_signal.version = signal.version
        db_signal.market = signal.market
        db_signal.category = signal.category
        db_signal.name = signal.name
        db_signal.direction = signal.direction.value
        db_signal.confidence = signal.confidence.value
        db_signal.last_updated = signal.last_updated
        db_signal.data_asof = signal.data_asof
        db_signal.explanation = signal.explanation
        db_signal.definition = signal.definition
        db_signal.source = signal.source
        db_signal.key_driver = signal.key_driver
        db_signal.validity_window = signal.validity_window.value
        db_signal.decay_behavior = signal.decay_behavior
        db_signal.related_signal_ids = signal.related_signal_ids
        db_signal.related_markets = signal.related_markets
        db_signal.signal_type = signal.signal_type.value
        db_signal.score = signal.score if signal.score is not None else calculate_signal_score(signal)
        db_signal.confidence_rationale = signal.confidence_rationale
        db_signal.updated_at = datetime.utcnow()
    else:
        # Create new
        db_signal = signal_to_db(signal)
        db.add(db_signal)
    
    db.commit()
    db.refresh(db_signal)
    return db_signal

def get_all_signals_db(db: Session) -> List[Signal]:
    """Get all signals from database."""
    db_signals = db.query(SignalDB).all()
    return [db_to_signal(s) for s in db_signals]

def get_signal_by_id_db(db: Session, signal_id: str) -> Optional[Signal]:
    """Get a signal by ID from database."""
    db_signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if db_signal:
        return db_to_signal(db_signal)
    return None

def save_snapshot_db(db: Session, snapshot: SignalSnapshot) -> SignalSnapshotDB:
    """Save a signal snapshot to database."""
    db_snapshot = SignalSnapshotDB(
        signal_id=snapshot.signal.signal_id,
        snapshot_date=snapshot.snapshot_date,
        signal_data=snapshot.signal.model_dump()
    )
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot

def get_snapshots_by_signal_db(db: Session, signal_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[SignalSnapshot]:
    """Get snapshots for a signal from database."""
    query = db.query(SignalSnapshotDB).filter(SignalSnapshotDB.signal_id == signal_id)
    
    if start_date:
        query = query.filter(SignalSnapshotDB.snapshot_date >= start_date)
    if end_date:
        query = query.filter(SignalSnapshotDB.snapshot_date <= end_date)
    
    db_snapshots = query.order_by(SignalSnapshotDB.snapshot_date.desc()).all()
    
    from .models import Signal, Direction, Confidence, ValidityWindow, SignalType
    
    snapshots = []
    for db_snap in db_snapshots:
        signal_data = db_snap.signal_data
        signal = Signal(**signal_data)
        snapshots.append(SignalSnapshot(
            signal=signal,
            snapshot_date=db_snap.snapshot_date
        ))
    
    return snapshots

def get_signals_at_date_db(db: Session, target_date: date) -> List[Signal]:
    """Get all signals as they were at a specific date."""
    # Get latest snapshot for each signal on or before target_date
    subquery = db.query(
        SignalSnapshotDB.signal_id,
        db.func.max(SignalSnapshotDB.snapshot_date).label('max_date')
    ).filter(
        SignalSnapshotDB.snapshot_date <= target_date
    ).group_by(SignalSnapshotDB.signal_id).subquery()
    
    db_snapshots = db.query(SignalSnapshotDB).join(
        subquery,
        and_(
            SignalSnapshotDB.signal_id == subquery.c.signal_id,
            SignalSnapshotDB.snapshot_date == subquery.c.max_date
        )
    ).all()
    
    from .models import Signal
    
    signals = []
    for db_snap in db_snapshots:
        signal_data = db_snap.signal_data
        signal = Signal(**signal_data)
        signals.append(signal)
    
    # If no snapshots, return current signals
    if not signals:
        return get_all_signals_db(db)
    
    return signals

