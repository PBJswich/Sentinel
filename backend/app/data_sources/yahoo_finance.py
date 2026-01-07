"""
Yahoo Finance adapter for price and technical data.

Uses yfinance library for free access to market data.
No API key required.
"""

import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from .base import BaseDataSource, DataSourceError
from ..models import Signal, Direction, Confidence, ValidityWindow, SignalType
from ..scoring import calculate_signal_score


class YahooFinanceAdapter(BaseDataSource):
    """
    Adapter for Yahoo Finance data.
    
    Fetches price data and calculates technical indicators.
    """
    
    def __init__(self, **kwargs):
        """Initialize Yahoo Finance adapter (no API key needed)."""
        super().__init__(api_key=None, **kwargs)
    
    def fetch_data(self, symbol: str, period: str = "1mo", **kwargs) -> Dict[str, Any]:
        """
        Fetch price data for a symbol.
        
        Args:
            symbol: Stock/commodity symbol (e.g., "CL=F" for WTI crude)
            period: Time period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            
        Returns:
            Dictionary with price data and metadata
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                raise DataSourceError(f"No data available for symbol: {symbol}")
            
            # Get current info
            info = ticker.info
            
            return {
                'symbol': symbol,
                'history': hist,
                'info': info,
                'current_price': hist['Close'].iloc[-1] if not hist.empty else None,
                'last_update': hist.index[-1] if not hist.empty else None,
            }
            
        except Exception as e:
            raise DataSourceError(f"Failed to fetch Yahoo Finance data for {symbol}: {str(e)}") from e
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_ma_crossover(self, prices: List[float], short_period: int = 20, long_period: int = 100) -> Optional[str]:
        """Calculate moving average crossover signal."""
        if len(prices) < long_period:
            return None
        
        short_ma = sum(prices[-short_period:]) / short_period
        long_ma = sum(prices[-long_period:]) / long_period
        
        if short_ma > long_ma:
            return "bullish"
        elif short_ma < long_ma:
            return "bearish"
        else:
            return "neutral"
    
    def transform_to_signal(self, raw_data: Dict[str, Any]) -> List[Signal]:
        """
        Transform price data into technical signals.
        
        Creates signals for:
        - RSI (overbought/oversold)
        - MA Crossover (trend)
        """
        signals = []
        symbol = raw_data['symbol']
        hist = raw_data['history']
        
        if hist.empty:
            return signals
        
        closes = hist['Close'].tolist()
        current_price = closes[-1]
        data_date = hist.index[-1].date() if hasattr(hist.index[-1], 'date') else date.today()
        
        # Map common symbols to market names
        symbol_to_market = {
            'CL=F': 'WTI Crude Oil',
            'BZ=F': 'Brent Crude Oil',
            'NG=F': 'Henry Hub Natural Gas',
            'GC=F': 'Gold',
            'HG=F': 'Copper',
            'ZC=F': 'Corn',
            'ZS=F': 'Soybeans',
        }
        
        market = symbol_to_market.get(symbol, symbol)
        
        # RSI Signal
        rsi = self._calculate_rsi(closes)
        if rsi is not None:
            if rsi < 30:
                direction = Direction.BULLISH
                confidence = Confidence.MEDIUM
                explanation = f"RSI at {rsi:.1f} indicates oversold conditions, potential bounce"
            elif rsi > 70:
                direction = Direction.BEARISH
                confidence = Confidence.MEDIUM
                explanation = f"RSI at {rsi:.1f} indicates overbought conditions, potential pullback"
            else:
                direction = Direction.NEUTRAL
                confidence = Confidence.LOW
                explanation = f"RSI at {rsi:.1f} indicates neutral momentum"
            
            rsi_signal = Signal(
                signal_id=f"yahoo_rsi_{symbol.lower().replace('=', '_')}",
                version="v1",
                market=market,
                category="Technical",
                name="RSI",
                direction=direction,
                confidence=confidence,
                last_updated=date.today(),
                data_asof=data_date,
                explanation=explanation,
                definition="Relative Strength Index (RSI) measures momentum. RSI < 30 is oversold (bullish), RSI > 70 is overbought (bearish).",
                source="Yahoo Finance price data",
                key_driver=f"RSI momentum indicator showing {direction.value} bias",
                validity_window=ValidityWindow.DAILY,
                decay_behavior="RSI signals decay over 1-2 days as price action evolves",
                related_signal_ids=[],
                related_markets=[],
                signal_type=SignalType.TACTICAL
            )
            rsi_signal.score = calculate_signal_score(rsi_signal)
            
            # Track lineage
            from ..data_lineage import track_lineage
            track_lineage(
                entity_id=rsi_signal.signal_id,
                entity_type="signal",
                source="yahoo_finance",
                source_id=symbol,
                transformation="rsi_calculation"
            )
            signals.append(rsi_signal)
        
        # MA Crossover Signal
        ma_signal_type = self._calculate_ma_crossover(closes)
        if ma_signal_type:
            if ma_signal_type == "bullish":
                direction = Direction.BULLISH
                confidence = Confidence.MEDIUM
                explanation = f"20-day MA above 100-day MA indicates uptrend"
            elif ma_signal_type == "bearish":
                direction = Direction.BEARISH
                confidence = Confidence.MEDIUM
                explanation = f"20-day MA below 100-day MA indicates downtrend"
            else:
                direction = Direction.NEUTRAL
                confidence = Confidence.LOW
                explanation = f"20-day and 100-day MAs are aligned, no clear trend"
            
            ma_signal = Signal(
                signal_id=f"yahoo_ma_{symbol.lower().replace('=', '_')}",
                version="v1",
                market=market,
                category="Technical",
                name="MA Crossover",
                direction=direction,
                confidence=confidence,
                last_updated=date.today(),
                data_asof=data_date,
                explanation=explanation,
                definition="20-day moving average vs 100-day moving average crossover. Bullish when short MA > long MA, bearish when short MA < long MA.",
                source="Yahoo Finance price data",
                key_driver=f"Moving average trend indicator showing {direction.value} bias",
                validity_window=ValidityWindow.DAILY,
                decay_behavior="MA crossover signals persist for weeks but weaken as price moves away from crossover point",
                related_signal_ids=[],
                related_markets=[],
                signal_type=SignalType.TACTICAL
            )
            ma_signal.score = calculate_signal_score(ma_signal)
            
            # Track lineage
            from ..data_lineage import track_lineage
            track_lineage(
                entity_id=ma_signal.signal_id,
                entity_type="signal",
                source="yahoo_finance",
                source_id=symbol,
                transformation="moving_average_crossover"
            )
            signals.append(ma_signal)
        
        return signals

