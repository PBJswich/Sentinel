"""
FRED (Federal Reserve Economic Data) API adapter.

Requires FRED API key (from https://fred.stlouisfed.org/docs/api/api_key.html)
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from .base import BaseDataSource, DataSourceError
from ..models import Signal, Direction, Confidence, ValidityWindow, SignalType
from ..scoring import calculate_signal_score


class FREDAdapter(BaseDataSource):
    """
    Adapter for FRED API data.
    
    Fetches economic indicators (DXY, yields, etc.)
    """
    
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    
    # Common FRED series IDs
    SERIES_IDS = {
        'DXY': 'DTWEXBGS',  # Trade-Weighted U.S. Dollar Index
        'US10Y': 'DGS10',   # 10-Year Treasury Constant Maturity Rate
        'US2Y': 'DGS2',     # 2-Year Treasury Constant Maturity Rate
        'VIX': 'VIXCLS',    # CBOE Volatility Index
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize FRED adapter.
        
        Args:
            api_key: FRED API key (required)
        """
        if not api_key:
            raise DataSourceError("FRED API key is required. Get one at https://fred.stlouisfed.org/docs/api/api_key.html")
        super().__init__(api_key=api_key, **kwargs)
    
    def fetch_data(self, series_id: str, days: int = 30, **kwargs) -> Dict[str, Any]:
        """
        Fetch data for a FRED series.
        
        Args:
            series_id: FRED series ID (e.g., 'DTWEXBGS' for DXY)
            days: Number of days of history to fetch
            
        Returns:
            Dictionary with series data
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d'),
                'sort_order': 'desc',
                'limit': 1000
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'observations' not in data:
                raise DataSourceError(f"No observations in FRED response for {series_id}")
            
            observations = data['observations']
            if not observations:
                raise DataSourceError(f"No data available for series {series_id}")
            
            # Filter out missing values
            valid_obs = [obs for obs in observations if obs.get('value') != '.']
            
            if not valid_obs:
                raise DataSourceError(f"No valid data points for series {series_id}")
            
            return {
                'series_id': series_id,
                'observations': valid_obs,
                'latest_value': float(valid_obs[0]['value']),
                'latest_date': valid_obs[0]['date'],
                'values': [float(obs['value']) for obs in valid_obs],
                'dates': [obs['date'] for obs in valid_obs]
            }
            
        except requests.RequestException as e:
            raise DataSourceError(f"FRED API request failed: {str(e)}") from e
        except (KeyError, ValueError, IndexError) as e:
            raise DataSourceError(f"Failed to parse FRED response: {str(e)}") from e
    
    def _calculate_trend(self, values: List[float]) -> Optional[str]:
        """Calculate trend direction from recent values."""
        if len(values) < 10:
            return None
        
        # Compare last 5 values to previous 5 values
        recent_avg = sum(values[:5]) / 5
        previous_avg = sum(values[5:10]) / 5
        
        if recent_avg > previous_avg * 1.01:  # 1% threshold
            return "bullish"
        elif recent_avg < previous_avg * 0.99:
            return "bearish"
        else:
            return "neutral"
    
    def transform_to_signal(self, raw_data: Dict[str, Any]) -> List[Signal]:
        """
        Transform FRED data into macro signals.
        
        Creates signals for:
        - USD strength (DXY trend)
        - Rates trend (10Y yield)
        """
        signals = []
        series_id = raw_data['series_id']
        values = raw_data['values']
        latest_value = raw_data['latest_value']
        latest_date = raw_data['latest_date']
        
        # Parse date
        try:
            data_date = date.fromisoformat(latest_date)
        except (ValueError, TypeError):
            data_date = date.today()
        
        # Map series IDs to market names and signal types
        series_info = {
            'DTWEXBGS': {
                'market': 'USD',
                'name': 'USD Strength',
                'category': 'Macro',
                'inverse': False  # Higher DXY = stronger USD = bearish for commodities
            },
            'DGS10': {
                'market': 'US10Y',
                'name': '10Y Yield Trend',
                'category': 'Macro',
                'inverse': False
            },
            'DGS2': {
                'market': 'US2Y',
                'name': '2Y Yield Trend',
                'category': 'Macro',
                'inverse': False
            },
        }
        
        info = series_info.get(series_id)
        if not info:
            return signals  # Unknown series, skip
        
        trend = self._calculate_trend(values)
        if not trend:
            return signals
        
        # For USD (DXY), inverse the signal for commodities
        if series_id == 'DTWEXBGS':
            # Strong USD (bullish DXY) is bearish for commodities
            if trend == "bullish":
                direction = Direction.BEARISH
                explanation = f"DXY at {latest_value:.2f} shows USD strength, bearish for commodities"
            elif trend == "bearish":
                direction = Direction.BULLISH
                explanation = f"DXY at {latest_value:.2f} shows USD weakness, bullish for commodities"
            else:
                direction = Direction.NEUTRAL
                explanation = f"DXY at {latest_value:.2f} shows stable USD"
        else:
            # For rates, use trend directly
            if trend == "bullish":
                direction = Direction.BULLISH
                explanation = f"{info['name']} at {latest_value:.2f} shows rising trend"
            elif trend == "bearish":
                direction = Direction.BEARISH
                explanation = f"{info['name']} at {latest_value:.2f} shows falling trend"
            else:
                direction = Direction.NEUTRAL
                explanation = f"{info['name']} at {latest_value:.2f} shows stable trend"
        
        confidence = Confidence.MEDIUM if trend != "neutral" else Confidence.LOW
        
        signal = Signal(
            signal_id=f"fred_{series_id.lower()}",
            version="v1",
            market=info['market'],
            category=info['category'],
            name=info['name'],
            direction=direction,
            confidence=confidence,
            last_updated=date.today(),
            data_asof=data_date,
            explanation=explanation,
            definition=f"{info['name']} trend based on FRED economic data. Calculated from recent value changes.",
            source="FRED API",
            key_driver=f"Macro trend indicator showing {direction.value} bias",
            validity_window=ValidityWindow.DAILY,
            decay_behavior="Macro signals persist for days to weeks but should be monitored daily",
            related_signal_ids=[],
            related_markets=[],
            signal_type=SignalType.STRUCTURAL
        )
        signal.score = calculate_signal_score(signal)
        
        # Track lineage
        from ..data_lineage import track_lineage
        track_lineage(
            entity_id=signal.signal_id,
            entity_type="signal",
            source="fred_api",
            source_id=series_id,
            transformation="trend_analysis"
        )
        signals.append(signal)
        
        return signals

