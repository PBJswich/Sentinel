"""
Data validation logic for signal quality checks.
"""

from typing import List, Optional
from datetime import date, timedelta
from ..models import Signal, Confidence, DataFreshness


class ValidationResult:
    """Result of validating a single signal."""
    
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self):
        return self.is_valid


class BatchValidationResult:
    """Result of validating a batch of signals."""
    
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.invalid = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.failed_signals: List[str] = []
    
    def add_result(self, signal_id: str, result: ValidationResult):
        """Add a validation result to the batch."""
        self.total += 1
        if result.is_valid:
            self.valid += 1
        else:
            self.invalid += 1
            self.failed_signals.append(signal_id)
        
        self.errors.extend(result.errors)
        self.warnings.extend(result.warnings)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.valid / self.total) * 100


class DataValidator:
    """Validates signal data quality and completeness."""
    
    def validate_signal(self, signal: Signal) -> ValidationResult:
        """
        Validate a single signal.
        
        Checks:
        - Completeness (required fields)
        - Data ranges (scores, percentages)
        - Consistency (direction matches data)
        - Freshness (not stale)
        """
        errors = []
        warnings = []
        
        # Completeness checks
        if not signal.explanation or len(signal.explanation.strip()) < 10:
            errors.append(f"Signal {signal.signal_id}: Explanation too short or missing")
        
        if not signal.definition:
            errors.append(f"Signal {signal.signal_id}: Missing definition")
        
        if not signal.source:
            errors.append(f"Signal {signal.signal_id}: Missing source")
        
        # Score range check
        if signal.score is not None:
            if signal.score < -1.0 or signal.score > 1.0:
                errors.append(f"Signal {signal.signal_id}: Score out of range: {signal.score}")
        
        # Timestamp checks
        if signal.data_asof > signal.last_updated:
            errors.append(f"Signal {signal.signal_id}: data_asof ({signal.data_asof}) is after last_updated ({signal.last_updated})")
        
        # Freshness checks
        days_old = (date.today() - signal.data_asof).days
        if days_old > 7:
            warnings.append(f"Signal {signal.signal_id}: Data is {days_old} days old")
        
        if signal.is_stale:
            warnings.append(f"Signal {signal.signal_id}: Signal is stale (age: {signal.age_days} days)")
        
        # Data freshness status
        if signal.data_freshness == DataFreshness.UNKNOWN:
            warnings.append(f"Signal {signal.signal_id}: Data freshness is unknown")
        
        # Confidence consistency
        # High confidence should have strong directional bias
        if signal.confidence == Confidence.HIGH and signal.direction.value == "neutral":
            warnings.append(f"Signal {signal.signal_id}: High confidence with neutral direction may be inconsistent")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings)
    
    def validate_batch(self, signals: List[Signal]) -> BatchValidationResult:
        """
        Validate a batch of signals.
        
        Returns aggregate validation results.
        """
        result = BatchValidationResult()
        
        for signal in signals:
            validation = self.validate_signal(signal)
            result.add_result(signal.signal_id, validation)
        
        return result
    
    def filter_valid_signals(self, signals: List[Signal]) -> tuple[List[Signal], List[Signal]]:
        """
        Separate valid and invalid signals.
        
        Returns:
            Tuple of (valid_signals, invalid_signals)
        """
        valid = []
        invalid = []
        
        for signal in signals:
            validation = self.validate_signal(signal)
            if validation.is_valid:
                valid.append(signal)
            else:
                invalid.append(signal)
        
        return valid, invalid

