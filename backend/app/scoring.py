"""
Signal scoring system.

Provides transparent, bounded scoring (-1 to +1) based on direction and confidence.
Scores are optional and never replace explanations.
"""

from typing import Optional, Dict
from .models import Signal, Direction, Confidence

def calculate_signal_score(signal: Signal) -> float:
    """
    Calculate a normalized score for a signal (-1 to +1).
    
    Scoring rules:
    - Direction: Bullish = +1, Bearish = -1, Neutral = 0
    - Confidence: High = 1.0, Medium = 0.6, Low = 0.3
    - Score = direction_value * confidence_multiplier
    
    Returns:
        Score between -1.0 (most bearish) and +1.0 (most bullish)
    """
    # Direction value
    if signal.direction == Direction.BULLISH:
        direction_value = 1.0
    elif signal.direction == Direction.BEARISH:
        direction_value = -1.0
    else:  # NEUTRAL
        direction_value = 0.0
    
    # Confidence multiplier
    if signal.confidence == Confidence.HIGH:
        confidence_multiplier = 1.0
    elif signal.confidence == Confidence.MEDIUM:
        confidence_multiplier = 0.6
    else:  # LOW
        confidence_multiplier = 0.3
    
    score = direction_value * confidence_multiplier
    
    # Ensure score is in valid range
    return max(-1.0, min(1.0, score))

def get_score_breakdown(signal: Signal) -> Dict:
    """
    Get detailed breakdown of how a signal score is calculated.
    
    Returns:
        Dictionary with score components and explanation
    """
    score = signal.score if signal.score is not None else calculate_signal_score(signal)
    
    direction_value = 1.0 if signal.direction == Direction.BULLISH else (-1.0 if signal.direction == Direction.BEARISH else 0.0)
    confidence_multiplier = 1.0 if signal.confidence == Confidence.HIGH else (0.6 if signal.confidence == Confidence.MEDIUM else 0.3)
    
    return {
        "score": round(score, 3),
        "direction": signal.direction.value,
        "direction_value": direction_value,
        "confidence": signal.confidence.value,
        "confidence_multiplier": confidence_multiplier,
        "calculation": f"{direction_value} * {confidence_multiplier} = {score:.3f}",
        "interpretation": _interpret_score(score)
    }

def _interpret_score(score: float) -> str:
    """Provide human-readable interpretation of a score."""
    if score >= 0.7:
        return "Strongly bullish"
    elif score >= 0.3:
        return "Moderately bullish"
    elif score >= -0.3:
        return "Neutral"
    elif score >= -0.7:
        return "Moderately bearish"
    else:
        return "Strongly bearish"

