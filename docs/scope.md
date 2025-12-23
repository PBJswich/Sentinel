# MVP Scope

## Markets (initial 9–10)
- WTI Crude
- Brent Crude
- Henry Hub Nat Gas
- Heating Oil
- RBOB Gasoline
- Gold
- Copper
- Corn
- Soybeans
- DXY (USD index proxy)
- US10Y (rates/real-yield proxy)

## Signal categories
- Macro
- Fundamental
- Sentiment
- Technical

## Signals per category (2–3 each)
- Macro: USD strength (DXY 20D vs 100D trend, return z-score); Rates/real-yield proxy (US10Y trend); Growth proxy (Copper/Gold ratio trend).
- Fundamental: Crude inventories vs seasonal (deviation z-score); Refinery utilization/runs trend; Curve structure tightness (front spread backwardation/contango). If nat gas in scope, add storage vs 5y average (weekly).
- Sentiment: News headline sentiment score + volume; COT spec positioning percentile/change (where available); Volatility risk sentiment (realized vol regime jump).
- Technical: Trend (20D/100D crossover + strength proxy); Momentum (14D and 63D z-scored); Mean reversion/overextension (RSI(14) extremes) or 20D breakout as a simple confirmation.

## Update frequency
- Daily: prices, macro proxies (DXY, US10Y), technicals, news sentiment; volatility regime check.
- Weekly: energy fundamentals (inventories, refinery runs), COT positioning, nat gas storage (if included).
- No intraday in MVP; key event timestamps can be appended later.

## What the dashboard shows
- Table of signals by commodity and pillar with timestamp/freshness.
- Direction: Bullish / Bearish / Neutral.
- Confidence: Low / Medium / High.
- Explanation: top contributing signals and brief rationale; surface missing/stale data flags.

