"""
Pipeline orchestrator for data ingestion.

Coordinates fetching, validation, transformation, and storage of signals.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import date
from ..models import Signal
from ..data_sources import YahooFinanceAdapter, FREDAdapter, DataSourceError
from .validators import DataValidator, BatchValidationResult
from ..db_service import save_signal_db
from ..database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the data ingestion pipeline."""
    
    def __init__(self):
        self.validator = DataValidator()
        self.adapters = {}
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize data source adapters."""
        # Yahoo Finance (no API key needed)
        self.adapters['yahoo'] = YahooFinanceAdapter()
        
        # FRED API (requires API key)
        fred_key = os.getenv('FRED_API_KEY')
        if fred_key:
            try:
                self.adapters['fred'] = FREDAdapter(api_key=fred_key)
            except Exception as e:
                logger.warning(f"Failed to initialize FRED adapter: {e}")
        else:
            logger.warning("FRED_API_KEY not set, FRED adapter disabled")
    
    def ingest_technical_signals(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Ingest technical signals from Yahoo Finance.
        
        Args:
            symbols: List of symbols to fetch (default: common commodity futures)
            
        Returns:
            Dictionary with ingestion results
        """
        if 'yahoo' not in self.adapters:
            return {'success': False, 'error': 'Yahoo Finance adapter not available'}
        
        if symbols is None:
            symbols = ['CL=F', 'GC=F', 'NG=F', 'HG=F']  # WTI, Gold, Nat Gas, Copper
        
        adapter = self.adapters['yahoo']
        all_signals = []
        errors = []
        
        for symbol in symbols:
            try:
                signals = adapter.fetch_and_transform(symbol=symbol, period='3mo')
                all_signals.extend(signals)
                logger.info(f"Fetched {len(signals)} signals for {symbol}")
            except DataSourceError as e:
                error_msg = f"Failed to fetch {symbol}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Validate signals
        validation_result = self.validator.validate_batch(all_signals)
        
        # Filter valid signals
        valid_signals, invalid_signals = self.validator.filter_valid_signals(all_signals)
        
        # Store valid signals
        stored_count = 0
        if valid_signals:
            stored_count = self._store_signals(valid_signals)
        
        return {
            'success': True,
            'total_fetched': len(all_signals),
            'valid': validation_result.valid,
            'invalid': validation_result.invalid,
            'stored': stored_count,
            'errors': errors + validation_result.errors,
            'warnings': validation_result.warnings,
            'failed_signals': [s.signal_id for s in invalid_signals]
        }
    
    def ingest_macro_signals(self, series_ids: List[str] = None) -> Dict[str, Any]:
        """
        Ingest macro signals from FRED API.
        
        Args:
            series_ids: List of FRED series IDs (default: DXY, 10Y yield)
            
        Returns:
            Dictionary with ingestion results
        """
        if 'fred' not in self.adapters:
            return {'success': False, 'error': 'FRED adapter not available (API key required)'}
        
        if series_ids is None:
            series_ids = ['DTWEXBGS', 'DGS10']  # DXY, 10Y yield
        
        adapter = self.adapters['fred']
        all_signals = []
        errors = []
        
        for series_id in series_ids:
            try:
                signals = adapter.fetch_and_transform(series_id=series_id, days=30)
                all_signals.extend(signals)
                logger.info(f"Fetched {len(signals)} signals for {series_id}")
            except DataSourceError as e:
                error_msg = f"Failed to fetch {series_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Validate signals
        validation_result = self.validator.validate_batch(all_signals)
        
        # Filter valid signals
        valid_signals, invalid_signals = self.validator.filter_valid_signals(all_signals)
        
        # Store valid signals
        stored_count = 0
        if valid_signals:
            stored_count = self._store_signals(valid_signals)
        
        return {
            'success': True,
            'total_fetched': len(all_signals),
            'valid': validation_result.valid,
            'invalid': validation_result.invalid,
            'stored': stored_count,
            'errors': errors + validation_result.errors,
            'warnings': validation_result.warnings,
            'failed_signals': [s.signal_id for s in invalid_signals]
        }
    
    def _store_signals(self, signals: List[Signal]) -> int:
        """
        Store signals to database.
        
        Returns:
            Number of signals successfully stored
        """
        db = SessionLocal()
        stored = 0
        
        try:
            for signal in signals:
                try:
                    save_signal_db(db, signal)
                    stored += 1
                except Exception as e:
                    logger.error(f"Failed to store signal {signal.signal_id}: {e}")
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit signals to database: {e}")
        finally:
            db.close()
        
        return stored
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.
        
        Fetches from all available sources and stores valid signals.
        """
        results = {
            'technical': None,
            'macro': None,
            'total_stored': 0,
            'errors': [],
            'warnings': []
        }
        
        # Ingest technical signals
        try:
            results['technical'] = self.ingest_technical_signals()
            if results['technical']['success']:
                results['total_stored'] += results['technical']['stored']
                results['errors'].extend(results['technical'].get('errors', []))
                results['warnings'].extend(results['technical'].get('warnings', []))
        except Exception as e:
            results['errors'].append(f"Technical signals ingestion failed: {str(e)}")
            logger.error(f"Technical signals ingestion failed: {e}")
        
        # Ingest macro signals
        try:
            results['macro'] = self.ingest_macro_signals()
            if results['macro']['success']:
                results['total_stored'] += results['macro']['stored']
                results['errors'].extend(results['macro'].get('errors', []))
                results['warnings'].extend(results['macro'].get('warnings', []))
        except Exception as e:
            results['errors'].append(f"Macro signals ingestion failed: {str(e)}")
            logger.error(f"Macro signals ingestion failed: {e}")
        
        results['success'] = len(results['errors']) == 0
        return results


def run_ingestion_pipeline() -> Dict[str, Any]:
    """
    Convenience function to run the full ingestion pipeline.
    
    Returns:
        Dictionary with pipeline results
    """
    orchestrator = PipelineOrchestrator()
    return orchestrator.run_full_pipeline()

