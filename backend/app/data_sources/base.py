"""
Base interface for data source adapters.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from ..models import Signal


class DataSourceError(Exception):
    """Exception raised by data source adapters."""
    pass


class BaseDataSource(ABC):
    """
    Base class for all data source adapters.
    
    Each adapter should implement methods to:
    1. Fetch raw data from the source
    2. Transform data to Signal models
    3. Validate data quality
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the data source adapter.
        
        Args:
            api_key: API key for the data source (if required)
            **kwargs: Additional configuration options
        """
        self.api_key = api_key
        self.config = kwargs
        self.last_fetch_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
    
    @abstractmethod
    def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """
        Fetch raw data from the data source.
        
        Args:
            **kwargs: Source-specific parameters (symbols, dates, etc.)
            
        Returns:
            Dictionary containing raw data from the source
            
        Raises:
            DataSourceError: If data fetch fails
        """
        pass
    
    @abstractmethod
    def transform_to_signal(self, raw_data: Dict[str, Any]) -> List[Signal]:
        """
        Transform raw data into Signal models.
        
        Args:
            raw_data: Raw data from fetch_data()
            
        Returns:
            List of Signal objects
        """
        pass
    
    def validate_data(self, raw_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate data quality and completeness.
        
        Args:
            raw_data: Raw data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not raw_data:
            errors.append("Empty data received")
            return False, errors
        
        if 'error' in raw_data:
            errors.append(f"API error: {raw_data.get('error')}")
            return False, errors
        
        return True, errors
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Get timestamp of last successful data fetch."""
        return self.last_fetch_time
    
    def fetch_and_transform(self, **kwargs) -> List[Signal]:
        """
        Convenience method: fetch data, validate, and transform.
        
        Args:
            **kwargs: Parameters passed to fetch_data()
            
        Returns:
            List of Signal objects
            
        Raises:
            DataSourceError: If fetch, validation, or transformation fails
        """
        try:
            raw_data = self.fetch_data(**kwargs)
            is_valid, errors = self.validate_data(raw_data)
            
            if not is_valid:
                error_msg = "; ".join(errors)
                self.last_error = error_msg
                raise DataSourceError(f"Data validation failed: {error_msg}")
            
            signals = self.transform_to_signal(raw_data)
            self.last_fetch_time = datetime.now()
            self.last_error = None
            
            return signals
            
        except Exception as e:
            self.last_error = str(e)
            raise DataSourceError(f"Failed to fetch and transform data: {str(e)}") from e

