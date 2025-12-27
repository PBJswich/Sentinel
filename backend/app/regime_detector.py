"""
Regime detection logic for macro environments.

Classifies macro regimes based on signal patterns:
- Inflationary growth: USD weak, rates rising, growth strong
- Risk-off: USD strong, rates falling, growth weak
- Tightening: USD strong, rates rising, growth mixed
- Disinflationary growth: USD mixed, rates stable, growth strong
"""

from datetime import date
from typing import Dict, List, Optional
from .models import Signal, Regime, RegimeType, Direction, Confidence
from .signal_loader import get_all_signals

def detect_regime(signals: Optional[List[Signal]] = None) -> Regime:
    """
    Detect current macro regime based on signal patterns.
    
    Args:
        signals: Optional list of signals (defaults to all signals)
        
    Returns:
        Detected regime with classification and indicators
    """
    if signals is None:
        signals = get_all_signals()
    
    # Filter to macro signals only
    macro_signals = [s for s in signals if s.category == "Macro"]
    
    if not macro_signals:
        return Regime(
            regime_type=RegimeType.UNCERTAIN,
            description="Unable to classify regime - no macro signals available",
            indicators={},
            impact={},
            detected_date=date.today(),
            confidence="Low"
        )
    
    # Extract USD, rates, and growth signals
    usd_signals = [s for s in macro_signals if "USD" in s.name or "DXY" in s.name]
    rates_signals = [s for s in macro_signals if "rate" in s.name.lower() or "yield" in s.name.lower() or "10Y" in s.name]
    growth_signals = [s for s in macro_signals if "growth" in s.name.lower() or "copper" in s.name.lower() or "equity" in s.name.lower()]
    
    # Determine USD strength (from signals)
    usd_strength = None
    if usd_signals:
        usd_directions = [s.direction for s in usd_signals]
        if Direction.BULLISH in usd_directions:
            usd_strength = "strong"
        elif Direction.BEARISH in usd_directions:
            usd_strength = "weak"
        else:
            usd_strength = "mixed"
    else:
        usd_strength = "unknown"
    
    # Determine rates direction
    rates_direction = None
    if rates_signals:
        rates_directions = [s.direction for s in rates_signals]
        if Direction.BULLISH in rates_directions:  # Bullish = rates rising
            rates_direction = "rising"
        elif Direction.BEARISH in rates_directions:  # Bearish = rates falling
            rates_direction = "falling"
        else:
            rates_direction = "stable"
    else:
        rates_direction = "unknown"
    
    # Determine growth strength
    growth_strength = None
    if growth_signals:
        growth_directions = [s.direction for s in growth_signals]
        if Direction.BULLISH in growth_directions:
            growth_strength = "strong"
        elif Direction.BEARISH in growth_directions:
            growth_strength = "weak"
        else:
            growth_strength = "mixed"
    else:
        growth_strength = "unknown"
    
    # Classify regime based on rules
    indicators = {
        "USD": usd_strength,
        "Rates": rates_direction,
        "Growth": growth_strength
    }
    
    # Rule 1: Inflationary growth (USD weak, rates rising, growth strong)
    if usd_strength == "weak" and rates_direction == "rising" and growth_strength == "strong":
        return Regime(
            regime_type=RegimeType.INFLATIONARY_GROWTH,
            description="Inflationary growth regime: Weak USD, rising rates, and strong growth suggest commodities should perform well, especially energy and industrial metals.",
            indicators=indicators,
            impact={
                "energy": "Bullish - strong demand and weak USD support prices",
                "metals": "Bullish - industrial metals benefit from growth, precious metals benefit from inflation",
                "ags": "Mixed - strong demand but potential cost pressures"
            },
            detected_date=date.today(),
            confidence="High" if all(v != "unknown" for v in indicators.values()) else "Medium"
        )
    
    # Rule 2: Risk-off (USD strong, rates falling, growth weak)
    if usd_strength == "strong" and rates_direction == "falling" and growth_strength == "weak":
        return Regime(
            regime_type=RegimeType.RISK_OFF,
            description="Risk-off regime: Strong USD, falling rates, and weak growth suggest defensive positioning. Precious metals may outperform, while industrial commodities face headwinds.",
            indicators=indicators,
            impact={
                "energy": "Bearish - weak demand and strong USD pressure prices",
                "metals": "Mixed - precious metals benefit from safe-haven flows, industrial metals suffer",
                "ags": "Bearish - weak demand and strong USD pressure prices"
            },
            detected_date=date.today(),
            confidence="High" if all(v != "unknown" for v in indicators.values()) else "Medium"
        )
    
    # Rule 3: Tightening (USD strong, rates rising, growth mixed)
    if usd_strength == "strong" and rates_direction == "rising" and growth_strength in ["mixed", "unknown"]:
        return Regime(
            regime_type=RegimeType.TIGHTENING,
            description="Tightening regime: Strong USD and rising rates suggest monetary tightening. Commodities face headwinds from stronger dollar and higher financing costs.",
            indicators=indicators,
            impact={
                "energy": "Bearish - strong USD and higher rates pressure prices",
                "metals": "Bearish - strong USD and higher rates pressure prices",
                "ags": "Bearish - strong USD and higher rates pressure prices"
            },
            detected_date=date.today(),
            confidence="High" if usd_strength != "unknown" and rates_direction != "unknown" else "Medium"
        )
    
    # Rule 4: Disinflationary growth (USD mixed, rates stable, growth strong)
    if usd_strength in ["mixed", "unknown"] and rates_direction == "stable" and growth_strength == "strong":
        return Regime(
            regime_type=RegimeType.DISINFLATIONARY_GROWTH,
            description="Disinflationary growth regime: Strong growth with stable rates suggests healthy expansion without inflation pressures. Commodities benefit from demand but face less inflation support.",
            indicators=indicators,
            impact={
                "energy": "Bullish - strong demand supports prices",
                "metals": "Bullish - industrial metals benefit from growth",
                "ags": "Bullish - strong demand supports prices"
            },
            detected_date=date.today(),
            confidence="High" if growth_strength == "strong" and rates_direction == "stable" else "Medium"
        )
    
    # Default: Uncertain
    return Regime(
        regime_type=RegimeType.UNCERTAIN,
        description="Uncertain regime: Signal patterns do not clearly match any defined regime classification.",
        indicators=indicators,
        impact={
            "energy": "Uncertain - mixed signals",
            "metals": "Uncertain - mixed signals",
            "ags": "Uncertain - mixed signals"
        },
        detected_date=date.today(),
        confidence="Low"
    )

def get_regime_impact_on_market(regime: Regime, market_group: str) -> str:
    """
    Get expected impact of a regime on a specific market group.
    
    Args:
        regime: The detected regime
        market_group: Market group (energy, metals, ags)
        
    Returns:
        Expected impact description
    """
    return regime.impact.get(market_group.lower(), "Impact uncertain")

