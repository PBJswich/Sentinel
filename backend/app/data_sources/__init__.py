"""
Data source adapters for real-time data ingestion.

Each adapter implements a common interface to fetch and transform
data from external sources into Signal models.
"""

from .base import BaseDataSource, DataSourceError
from .yahoo_finance import YahooFinanceAdapter
from .fred_api import FREDAdapter

__all__ = [
    'BaseDataSource',
    'DataSourceError',
    'YahooFinanceAdapter',
    'FREDAdapter',
]

