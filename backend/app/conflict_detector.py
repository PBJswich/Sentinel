"""
Conflict detection logic for signals.

Detects conflicts between signals based on rules:
- Same market, opposite directions, high confidence
- Structural vs tactical mismatch
- Timeframe mismatch (intraday vs structural)
"""

from typing import List
from .models import Signal, Conflict, ConflictType, Direction, SignalType, ValidityWindow
from .signal_loader import get_all_signals

def detect_conflicts(signals: List[Signal]) -> List[Conflict]:
    """
    Detect conflicts between signals based on rules.
    
    Args:
        signals: List of signals to analyze
        
    Returns:
        List of detected conflicts
    """
    conflicts = []
    signal_map = {s.signal_id: s for s in signals}
    
    # Rule 1: Same market, opposite directions, high confidence
    by_market = {}
    for signal in signals:
        if signal.market not in by_market:
            by_market[signal.market] = []
        by_market[signal.market].append(signal)
    
    for market, market_signals in by_market.items():
        if len(market_signals) < 2:
            continue
            
        # Find opposite directions with high confidence
        bullish_high = [s for s in market_signals if s.direction == Direction.BULLISH and s.confidence.value == "High"]
        bearish_high = [s for s in market_signals if s.direction == Direction.BEARISH and s.confidence.value == "High"]
        
        if bullish_high and bearish_high:
            conflicting_ids = [s.signal_id for s in bullish_high + bearish_high]
            conflicts.append(Conflict(
                conflicting_signals=conflicting_ids,
                conflict_type=ConflictType.OPPOSITE_DIRECTION,
                description=f"High confidence signals in {market} show opposite directions: {len(bullish_high)} bullish vs {len(bearish_high)} bearish",
                market=market
            ))
    
    # Rule 2: Structural vs tactical mismatch (same market, opposite directions)
    for market, market_signals in by_market.items():
        if len(market_signals) < 2:
            continue
            
        structural_bullish = [s for s in market_signals if s.signal_type == SignalType.STRUCTURAL and s.direction == Direction.BULLISH]
        tactical_bearish = [s for s in market_signals if s.signal_type == SignalType.TACTICAL and s.direction == Direction.BEARISH]
        structural_bearish = [s for s in market_signals if s.signal_type == SignalType.STRUCTURAL and s.direction == Direction.BEARISH]
        tactical_bullish = [s for s in market_signals if s.signal_type == SignalType.TACTICAL and s.direction == Direction.BULLISH]
        
        if (structural_bullish and tactical_bearish) or (structural_bearish and tactical_bullish):
            conflicting_ids = []
            if structural_bullish and tactical_bearish:
                conflicting_ids = [s.signal_id for s in structural_bullish + tactical_bearish]
                tension_desc = "Structural bullish forces conflict with tactical bearish signals"
            else:
                conflicting_ids = [s.signal_id for s in structural_bearish + tactical_bullish]
                tension_desc = "Structural bearish forces conflict with tactical bullish signals"
            
            conflicts.append(Conflict(
                conflicting_signals=conflicting_ids,
                conflict_type=ConflictType.STRUCTURAL_TACTICAL_MISMATCH,
                description=f"Structural vs tactical mismatch in {market}: {tension_desc}",
                market=market,
                structural_vs_transient=tension_desc
            ))
    
    # Rule 3: Timeframe mismatch (intraday/daily vs structural)
    for market, market_signals in by_market.items():
        if len(market_signals) < 2:
            continue
            
        short_term = [s for s in market_signals if s.validity_window in [ValidityWindow.INTRADAY, ValidityWindow.DAILY]]
        structural = [s for s in market_signals if s.validity_window == ValidityWindow.STRUCTURAL]
        
        if short_term and structural:
            # Check if they have opposite directions
            short_bullish = [s for s in short_term if s.direction == Direction.BULLISH]
            short_bearish = [s for s in short_term if s.direction == Direction.BEARISH]
            struct_bullish = [s for s in structural if s.direction == Direction.BULLISH]
            struct_bearish = [s for s in structural if s.direction == Direction.BEARISH]
            
            if (short_bullish and struct_bearish) or (short_bearish and struct_bullish):
                conflicting_ids = [s.signal_id for s in short_term + structural]
                if short_bullish and struct_bearish:
                    mismatch_desc = "Short-term bullish signals conflict with structural bearish trend"
                else:
                    mismatch_desc = "Short-term bearish signals conflict with structural bullish trend"
                
                conflicts.append(Conflict(
                    conflicting_signals=conflicting_ids,
                    conflict_type=ConflictType.TIMEFRAME_MISMATCH,
                    description=f"Timeframe mismatch in {market}: {mismatch_desc}",
                    market=market,
                    timeframe_mismatch=mismatch_desc
                ))
    
    return conflicts

def get_conflicts_for_market(market: str, signals: List[Signal] = None) -> List[Conflict]:
    """Get conflicts for a specific market."""
    if signals is None:
        signals = get_all_signals()
    
    market_signals = [s for s in signals if s.market == market]
    return detect_conflicts(market_signals)

def get_all_conflicts(signals: List[Signal] = None) -> List[Conflict]:
    """Get all conflicts across all signals."""
    if signals is None:
        signals = get_all_signals()
    
    return detect_conflicts(signals)

