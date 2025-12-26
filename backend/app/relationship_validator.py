"""
Relationship validation for signals.

Ensures that referenced signals exist and relationships are valid.
"""

from typing import List, Set
from .models import Signal
from .signal_loader import get_all_signals

def validate_signal_relationships(signals: List[Signal] = None) -> List[str]:
    """
    Validate that all referenced signal IDs exist.
    
    Args:
        signals: List of signals to validate. If None, loads all signals.
        
    Returns:
        List of validation error messages (empty if all valid)
    """
    if signals is None:
        signals = get_all_signals()
    
    errors = []
    signal_ids = {s.signal_id for s in signals}
    
    for signal in signals:
        # Validate related_signal_ids
        for related_id in signal.related_signal_ids:
            if related_id not in signal_ids:
                errors.append(
                    f"Signal {signal.signal_id} references non-existent signal: {related_id}"
                )
        
        # Validate that signal doesn't reference itself
        if signal.signal_id in signal.related_signal_ids:
            errors.append(
                f"Signal {signal.signal_id} references itself in related_signal_ids"
            )
    
    return errors

def validate_all_relationships() -> dict:
    """
    Validate all signal relationships and return validation report.
    
    Returns:
        Dictionary with validation results
    """
    signals = get_all_signals()
    errors = validate_signal_relationships(signals)
    
    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
        "total_signals": len(signals),
        "signals_with_relationships": sum(1 for s in signals if s.related_signal_ids)
    }

