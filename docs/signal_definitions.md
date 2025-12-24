# Signal Definitions

This document defines the signal categories and types used in the Cross-Commodity Signal Dashboard.

## Signal Categories

### Technical

Technical signals are derived from price action, volume, and technical indicators. They focus on timing and trend identification.

**Characteristics:**
- Based on historical price/volume data
- Short to medium-term timeframes
- Used for entry/exit timing
- Examples: RSI, Moving Averages, Support/Resistance

**Current Signals:**
- **RSI (Relative Strength Index)**: Momentum oscillator indicating overbought/oversold conditions
- **Moving Average Crossover**: Trend signal when short-term MA crosses above/below long-term MA

---

### Macro

Macro signals capture broad economic and cross-asset factors that influence commodity prices. They reflect regime changes and systemic drivers.

**Characteristics:**
- Cross-asset and economic indicators
- Medium to long-term impact
- Regime-defining factors
- Examples: USD strength, interest rates, growth proxies

**Current Signals:**
- **USD Trend**: U.S. dollar strength/weakness affecting commodity prices (inverse relationship for most commodities)

---

### Fundamental

Fundamental signals are based on supply/demand dynamics, inventory levels, and physical market conditions specific to each commodity.

**Characteristics:**
- Market-specific supply/demand data
- Physical market indicators
- Weekly or event-driven updates
- Examples: Inventory levels, production data, consumption metrics

**Current Signals:**
- **Crude Inventories**: Weekly EIA inventory data compared to seasonal averages, indicating supply tightness or surplus

---

### Sentiment

Sentiment signals capture market positioning, news flow, and narrative shifts that can drive short-term price movements.

**Characteristics:**
- Positioning and flow data
- News sentiment analysis
- Crowded trade detection
- Examples: COT positioning, news sentiment, volatility regimes

**Current Signals:**
- **COT Positioning**: Commitments of Traders report showing speculative positioning extremes

---

## Signal Properties

### Direction

- **Bullish**: Signal suggests upward price movement
- **Bearish**: Signal suggests downward price movement
- **Neutral**: Signal suggests no clear directional bias or mixed signals

### Confidence

- **High**: Strong conviction, clear signal, reliable data
- **Medium**: Moderate conviction, some uncertainty or mixed factors
- **Low**: Weak conviction, early signal, or conflicting indicators

### Update Frequency

- **Daily**: Updated each trading day
- **Weekly**: Updated on specific release days (e.g., EIA inventory reports)
- **Event-driven**: Updated when specific events occur (e.g., Fed decisions, major economic releases)

## Signal Structure

Each signal follows this consistent structure:

```
Market: [Commodity name]
Category: [Technical | Macro | Fundamental | Sentiment]
Signal Name: [Specific indicator name]
Direction: [Bullish | Bearish | Neutral]
Confidence: [Low | Medium | High]
Updated: [Date]
Explanation: [1-2 sentence human-readable explanation]
```

## Interpretation Guidelines

1. **Multiple signals per market**: A commodity may have multiple signals across categories. Look for alignment or divergence.

2. **Confidence matters**: High confidence signals should carry more weight in decision-making than low confidence ones.

3. **Category complementarity**: 
   - Technical signals provide timing
   - Macro signals provide context
   - Fundamental signals provide market-specific drivers
   - Sentiment signals provide positioning context

4. **Direction alignment**: When multiple signals align in direction and confidence, the signal is stronger.

5. **Neutral signals**: Neutral doesn't mean "ignore" - it may indicate a transition period or balanced forces.

## Future Signal Types (Not in MVP)

- **Cross-commodity spreads**: Relative value between related commodities
- **Curve structure**: Term structure signals (backwardation/contango)
- **Volatility regimes**: Risk-on/risk-off indicators
- **Correlation shifts**: Changing relationships between assets

