"""
Signal analysis features.

Provides composite signals, correlation analysis, performance metrics, and predictive signals.
"""

from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from collections import defaultdict
import statistics
from .models import Signal, Direction, Confidence
from .scoring import calculate_signal_score


# Pillar weights for composite signals
# These can be adjusted based on importance/confidence in each pillar
DEFAULT_PILLAR_WEIGHTS = {
    "Macro": 0.35,      # Macro signals are often most important
    "Fundamental": 0.30, # Fundamentals drive long-term moves
    "Technical": 0.20,  # Technicals provide timing
    "Sentiment": 0.15   # Sentiment can be noisy but important
}


def calculate_composite_signal(
    signals: List[Signal],
    market: str,
    pillar_weights: Optional[Dict[str, float]] = None,
    min_signals_per_pillar: int = 1
) -> Optional[Dict]:
    """
    Calculate a composite signal from multiple pillar signals for a market.
    
    A composite signal combines signals across different pillars (categories)
    using weighted averages based on:
    - Signal scores (-1 to +1)
    - Pillar weights (importance of each pillar)
    - Confidence levels (higher confidence signals weighted more)
    
    Args:
        signals: List of signals for the market (should include multiple pillars)
        market: Market name
        pillar_weights: Optional custom weights for pillars (defaults to DEFAULT_PILLAR_WEIGHTS)
        min_signals_per_pillar: Minimum signals required per pillar to include in composite
        
    Returns:
        Dictionary with composite signal data, or None if insufficient signals
    """
    if not signals:
        return None
    
    if pillar_weights is None:
        pillar_weights = DEFAULT_PILLAR_WEIGHTS.copy()
    
    # Group signals by pillar (category)
    by_pillar = defaultdict(list)
    for signal in signals:
        by_pillar[signal.category].append(signal)
    
    # Check if we have enough signals
    if len(by_pillar) < 2:
        return None  # Need at least 2 different pillars
    
    # Calculate weighted score per pillar
    pillar_scores = {}
    pillar_weights_used = {}
    pillar_directions = {}
    pillar_confidences = {}
    
    for pillar, pillar_signals in by_pillar.items():
        if len(pillar_signals) < min_signals_per_pillar:
            continue  # Skip pillars with insufficient signals
        
        # Calculate average score for this pillar
        scores = []
        confidences = []
        directions = []
        
        for signal in pillar_signals:
            score = signal.score if signal.score is not None else calculate_signal_score(signal)
            scores.append(score)
            confidences.append(signal.confidence)
            directions.append(signal.direction)
        
        # Weight by confidence: High=1.0, Medium=0.6, Low=0.3
        confidence_weights = {
            Confidence.HIGH: 1.0,
            Confidence.MEDIUM: 0.6,
            Confidence.LOW: 0.3
        }
        
        weighted_scores = [
            score * confidence_weights.get(conf, 0.3)
            for score, conf in zip(scores, confidences)
        ]
        
        # Average weighted score
        if weighted_scores:
            pillar_score = sum(weighted_scores) / len(weighted_scores)
            pillar_scores[pillar] = pillar_score
            pillar_weights_used[pillar] = pillar_weights.get(pillar, 0.25)
            
            # Determine dominant direction
            bullish_count = sum(1 for d in directions if d == Direction.BULLISH)
            bearish_count = sum(1 for d in directions if d == Direction.BEARISH)
            if bullish_count > bearish_count:
                pillar_directions[pillar] = "Bullish"
            elif bearish_count > bullish_count:
                pillar_directions[pillar] = "Bearish"
            else:
                pillar_directions[pillar] = "Neutral"
            
            # Average confidence
            conf_values = {
                Confidence.HIGH: 3,
                Confidence.MEDIUM: 2,
                Confidence.LOW: 1
            }
            avg_conf_num = sum(conf_values.get(c, 1) for c in confidences) / len(confidences)
            if avg_conf_num >= 2.5:
                pillar_confidences[pillar] = "High"
            elif avg_conf_num >= 1.5:
                pillar_confidences[pillar] = "Medium"
            else:
                pillar_confidences[pillar] = "Low"
    
    if not pillar_scores:
        return None
    
    # Normalize pillar weights to sum to 1.0
    total_weight = sum(pillar_weights_used.values())
    if total_weight == 0:
        return None
    
    normalized_weights = {k: v / total_weight for k, v in pillar_weights_used.items()}
    
    # Calculate composite score
    composite_score = sum(
        pillar_scores[pillar] * normalized_weights[pillar]
        for pillar in pillar_scores.keys()
    )
    
    # Determine composite direction
    if composite_score >= 0.3:
        composite_direction = "Bullish"
    elif composite_score <= -0.3:
        composite_direction = "Bearish"
    else:
        composite_direction = "Neutral"
    
    # Calculate composite confidence (weighted average)
    conf_values = {"High": 3, "Medium": 2, "Low": 1}
    weighted_conf = sum(
        conf_values.get(pillar_confidences[pillar], 1) * normalized_weights[pillar]
        for pillar in pillar_confidences.keys()
    )
    
    if weighted_conf >= 2.5:
        composite_confidence = "High"
    elif weighted_conf >= 1.5:
        composite_confidence = "Medium"
    else:
        composite_confidence = "Low"
    
    # Build explanation
    contributing_pillars = []
    for pillar in sorted(pillar_scores.keys()):
        score = pillar_scores[pillar]
        direction = pillar_directions[pillar]
        confidence = pillar_confidences[pillar]
        contributing_pillars.append({
            "pillar": pillar,
            "score": round(score, 3),
            "direction": direction,
            "confidence": confidence,
            "weight": round(normalized_weights[pillar], 3),
            "signal_count": len(by_pillar[pillar])
        })
    
    explanation = f"Composite signal combining {len(contributing_pillars)} pillars: "
    explanation += ", ".join([f"{p['pillar']} ({p['direction']})" for p in contributing_pillars])
    
    return {
        "market": market,
        "composite_score": round(composite_score, 3),
        "composite_direction": composite_direction,
        "composite_confidence": composite_confidence,
        "pillar_breakdown": contributing_pillars,
        "explanation": explanation,
        "pillar_count": len(contributing_pillars),
        "total_signals": len(signals),
        "calculated_at": datetime.utcnow().isoformat()
    }


def calculate_signal_correlation(
    signal1: Signal,
    signal2: Signal,
    historical_snapshots: Optional[List[Tuple[date, Signal, Signal]]] = None
) -> Dict:
    """
    Calculate correlation between two signals.
    
    Correlation is based on:
    - Score alignment (how often they move together)
    - Direction agreement
    - Confidence similarity
    
    Args:
        signal1: First signal
        signal2: Second signal
        historical_snapshots: Optional list of (date, signal1_snapshot, signal2_snapshot) tuples
        
    Returns:
        Dictionary with correlation metrics
    """
    # Current correlation (based on current scores)
    score1 = signal1.score if signal1.score is not None else calculate_signal_score(signal1)
    score2 = signal2.score if signal2.score is not None else calculate_signal_score(signal2)
    
    # Score correlation (Pearson-like, simplified)
    # If both positive or both negative, positive correlation
    score_correlation = 1.0 if (score1 * score2) >= 0 else -1.0
    if abs(score1) < 0.1 or abs(score2) < 0.1:
        score_correlation = 0.0  # Neutral signals don't correlate well
    
    # Direction agreement
    direction_agreement = 1.0 if signal1.direction == signal2.direction else 0.0
    
    # Combined correlation score
    correlation_score = (score_correlation * 0.7) + (direction_agreement * 0.3)
    
    # Historical correlation if snapshots provided
    historical_correlation = None
    if historical_snapshots and len(historical_snapshots) > 1:
        scores1 = []
        scores2 = []
        for _, s1, s2 in historical_snapshots:
            sc1 = s1.score if s1.score is not None else calculate_signal_score(s1)
            sc2 = s2.score if s2.score is not None else calculate_signal_score(s2)
            scores1.append(sc1)
            scores2.append(sc2)
        
        if len(scores1) > 1:
            # Calculate Pearson correlation coefficient
            try:
                mean1 = statistics.mean(scores1)
                mean2 = statistics.mean(scores2)
                
                numerator = sum((s1 - mean1) * (s2 - mean2) for s1, s2 in zip(scores1, scores2))
                denom1 = sum((s1 - mean1) ** 2 for s1 in scores1)
                denom2 = sum((s2 - mean2) ** 2 for s2 in scores2)
                
                if denom1 > 0 and denom2 > 0:
                    historical_correlation = numerator / ((denom1 * denom2) ** 0.5)
                    historical_correlation = max(-1.0, min(1.0, historical_correlation))
            except (ZeroDivisionError, ValueError):
                pass
    
    return {
        "signal1_id": signal1.signal_id,
        "signal2_id": signal2.signal_id,
        "correlation_score": round(correlation_score, 3),
        "score_correlation": round(score_correlation, 3),
        "direction_agreement": direction_agreement,
        "historical_correlation": round(historical_correlation, 3) if historical_correlation is not None else None,
        "historical_periods": len(historical_snapshots) if historical_snapshots else 0,
        "interpretation": _interpret_correlation(correlation_score)
    }


def _interpret_correlation(score: float) -> str:
    """Interpret correlation score."""
    if score >= 0.7:
        return "Strongly correlated"
    elif score >= 0.3:
        return "Moderately correlated"
    elif score >= -0.3:
        return "Weakly correlated"
    elif score >= -0.7:
        return "Moderately inversely correlated"
    else:
        return "Strongly inversely correlated"


def analyze_signal_performance(
    signal_id: str,
    historical_snapshots: List[Tuple[date, Signal]],
    price_data: Optional[List[Tuple[date, float]]] = None
) -> Dict:
    """
    Analyze signal performance over time.
    
    This is a simplified backtesting framework that tracks:
    - Signal accuracy (how often direction was correct)
    - Signal persistence (how long signals lasted)
    - Score vs outcome correlation
    
    Args:
        signal_id: Signal ID to analyze
        historical_snapshots: List of (date, signal) tuples
        price_data: Optional list of (date, price) tuples for validation
        
    Returns:
        Dictionary with performance metrics
    """
    if not historical_snapshots or len(historical_snapshots) < 2:
        return {
            "signal_id": signal_id,
            "error": "Insufficient historical data",
            "periods_analyzed": len(historical_snapshots) if historical_snapshots else 0
        }
    
    # Sort by date
    historical_snapshots = sorted(historical_snapshots, key=lambda x: x[0])
    
    # Track direction changes
    direction_changes = 0
    score_changes = []
    signal_durations = []
    
    prev_direction = None
    prev_score = None
    signal_start_date = historical_snapshots[0][0]
    
    for date, signal in historical_snapshots:
        if prev_direction is not None:
            if signal.direction != prev_direction:
                direction_changes += 1
                # Calculate duration of previous signal
                duration = (date - signal_start_date).days
                signal_durations.append(duration)
                signal_start_date = date
            
            if prev_score is not None:
                score_change = abs(signal.score - prev_score) if signal.score is not None else 0
                score_changes.append(score_change)
        
        prev_direction = signal.direction
        prev_score = signal.score if signal.score is not None else calculate_signal_score(signal)
    
    # Calculate final duration
    if len(historical_snapshots) > 1:
        final_duration = (historical_snapshots[-1][0] - signal_start_date).days
        signal_durations.append(final_duration)
    
    # Basic metrics
    avg_duration = statistics.mean(signal_durations) if signal_durations else 0
    avg_score_change = statistics.mean(score_changes) if score_changes else 0
    
    # If price data available, calculate accuracy
    accuracy = None
    if price_data and len(price_data) > 1:
        price_data_dict = dict(price_data)
        correct_predictions = 0
        total_predictions = 0
        
        for i in range(len(historical_snapshots) - 1):
            date1, signal1 = historical_snapshots[i]
            date2, signal2 = historical_snapshots[i + 1]
            
            # Check if price moved in predicted direction
            if date1 in price_data_dict and date2 in price_data_dict:
                price_change = price_data_dict[date2] - price_data_dict[date1]
                predicted_direction = signal1.direction
                
                if price_change > 0 and predicted_direction == Direction.BULLISH:
                    correct_predictions += 1
                elif price_change < 0 and predicted_direction == Direction.BEARISH:
                    correct_predictions += 1
                elif price_change == 0 and predicted_direction == Direction.NEUTRAL:
                    correct_predictions += 1
                
                total_predictions += 1
        
        if total_predictions > 0:
            accuracy = correct_predictions / total_predictions
    
    return {
        "signal_id": signal_id,
        "periods_analyzed": len(historical_snapshots),
        "direction_changes": direction_changes,
        "average_signal_duration_days": round(avg_duration, 1) if avg_duration else 0,
        "average_score_change": round(avg_score_change, 3) if avg_score_change else 0,
        "prediction_accuracy": round(accuracy, 3) if accuracy is not None else None,
        "analysis_period": {
            "start": historical_snapshots[0][0].isoformat(),
            "end": historical_snapshots[-1][0].isoformat()
        }
    }


def generate_predictive_signal(
    market: str,
    signals: List[Signal],
    historical_trends: Optional[List[Tuple[date, float]]] = None
) -> Optional[Dict]:
    """
    Generate a predictive signal based on current signals and trends.
    
    This is a rule-based predictive system (not ML) that:
    - Identifies momentum patterns
    - Detects convergence/divergence across pillars
    - Predicts likely direction changes based on signal strength
    
    Args:
        market: Market name
        signals: Current signals for the market
        historical_trends: Optional list of (date, score) tuples showing historical trend
        
    Returns:
        Dictionary with predictive signal, or None if insufficient data
    """
    if not signals:
        return None
    
    # Calculate composite signal
    composite = calculate_composite_signal(signals, market)
    if not composite:
        return None
    
    composite_score = composite["composite_score"]
    composite_direction = composite["composite_direction"]
    
    # Analyze momentum if historical data available
    momentum = None
    if historical_trends and len(historical_trends) >= 3:
        recent_scores = [score for _, score in historical_trends[-3:]]
        if len(recent_scores) >= 2:
            # Simple momentum: recent trend
            momentum = recent_scores[-1] - recent_scores[0]
    
    # Rule-based predictions
    predictions = []
    confidence = "Low"
    
    # Strong composite signal with momentum
    if abs(composite_score) >= 0.6:
        if momentum and momentum * composite_score > 0:
            # Momentum aligns with signal - strong continuation
            predicted_direction = composite_direction
            confidence = "High"
            predictions.append("Strong signal with aligned momentum suggests continuation")
        elif momentum and abs(momentum) > 0.3:
            # Momentum diverges - potential reversal
            predicted_direction = "Bearish" if composite_direction == "Bullish" else "Bullish"
            confidence = "Medium"
            predictions.append("Strong signal but momentum divergence suggests potential reversal")
        else:
            # Strong signal, no clear momentum
            predicted_direction = composite_direction
            confidence = "Medium"
            predictions.append("Strong signal but limited momentum data")
    
    # Moderate composite signal
    elif abs(composite_score) >= 0.3:
        if momentum and abs(momentum) > 0.2:
            # Momentum provides direction
            if momentum > 0:
                predicted_direction = "Bullish"
            else:
                predicted_direction = "Bearish"
            confidence = "Medium"
            predictions.append("Moderate signal with momentum suggesting direction")
        else:
            # Weak signal
            predicted_direction = composite_direction
            confidence = "Low"
            predictions.append("Moderate signal strength, limited predictive power")
    
    # Weak composite signal
    else:
        if momentum and abs(momentum) > 0.3:
            # Momentum stronger than signal
            if momentum > 0:
                predicted_direction = "Bullish"
            else:
                predicted_direction = "Bearish"
            confidence = "Low"
            predictions.append("Weak signal but momentum suggests direction")
        else:
            # Very weak - predict neutral
            predicted_direction = "Neutral"
            confidence = "Low"
            predictions.append("Weak signal and momentum, predicting neutral")
    
    # Check for convergence (all pillars agree)
    pillar_directions = [p["direction"] for p in composite["pillar_breakdown"]]
    if len(set(pillar_directions)) == 1:
        # All pillars agree
        if confidence == "Low":
            confidence = "Medium"
        predictions.append("All pillars converge on same direction")
    
    # Check for divergence (pillars disagree)
    if len(set(pillar_directions)) == len(pillar_directions):
        # All pillars different
        confidence = "Low"
        predictions.append("Pillars diverge, reducing confidence")
    
    explanation = "Predictive signal based on: " + "; ".join(predictions)
    
    return {
        "market": market,
        "predicted_direction": predicted_direction,
        "predicted_confidence": confidence,
        "current_composite_score": composite_score,
        "current_composite_direction": composite_direction,
        "momentum": round(momentum, 3) if momentum is not None else None,
        "explanation": explanation,
        "prediction_rationale": predictions,
        "based_on_pillars": len(composite["pillar_breakdown"]),
        "calculated_at": datetime.utcnow().isoformat()
    }

