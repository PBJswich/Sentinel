"""
ETL Pipeline Framework.

Bronze → Silver → Gold data pipeline pattern.
This is a simplified framework that can be extended for full Snowflake/Databricks integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class DataLayer(str, Enum):
    """Data pipeline layers."""
    BRONZE = "bronze"  # Raw data ingestion
    SILVER = "silver"  # Cleaned and validated data
    GOLD = "gold"  # Business-ready aggregated data

@dataclass
class PipelineStage:
    """ETL pipeline stage."""
    stage_name: str
    layer: DataLayer
    input_source: str
    output_target: str
    transformation: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    records_processed: int = 0
    errors: List[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

# Pipeline execution history
_pipeline_runs: List[PipelineStage] = []

def execute_bronze_stage(source: str, raw_data: Any) -> Dict:
    """
    Bronze stage: Raw data ingestion.
    
    Args:
        source: Data source name (e.g., "yahoo_finance", "fred_api")
        raw_data: Raw data from source
        
    Returns:
        Stage execution result
    """
    stage = PipelineStage(
        stage_name=f"bronze_{source}",
        layer=DataLayer.BRONZE,
        input_source=source,
        output_target="bronze_storage",
        status="running",
        started_at=datetime.utcnow()
    )
    
    try:
        # In a real implementation, this would write to bronze storage
        # For now, we just track the stage
        stage.records_processed = len(raw_data) if isinstance(raw_data, (list, dict)) else 1
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
    except Exception as e:
        stage.status = "failed"
        stage.errors.append(str(e))
        stage.completed_at = datetime.utcnow()
    
    _pipeline_runs.append(stage)
    
    return {
        "stage": stage.stage_name,
        "status": stage.status,
        "records_processed": stage.records_processed,
        "errors": stage.errors
    }

def execute_silver_stage(bronze_data: Any, validation_rules: Optional[List] = None) -> Dict:
    """
    Silver stage: Data cleaning and validation.
    
    Args:
        bronze_data: Data from bronze stage
        validation_rules: Optional validation rules to apply
        
    Returns:
        Stage execution result
    """
    stage = PipelineStage(
        stage_name="silver_cleaning",
        layer=DataLayer.SILVER,
        input_source="bronze_storage",
        output_target="silver_storage",
        transformation="clean_and_validate",
        status="running",
        started_at=datetime.utcnow()
    )
    
    try:
        # In a real implementation, this would:
        # 1. Clean data (remove duplicates, fix formats)
        # 2. Validate against rules
        # 3. Write to silver storage
        
        stage.records_processed = len(bronze_data) if isinstance(bronze_data, (list, dict)) else 1
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
    except Exception as e:
        stage.status = "failed"
        stage.errors.append(str(e))
        stage.completed_at = datetime.utcnow()
    
    _pipeline_runs.append(stage)
    
    return {
        "stage": stage.stage_name,
        "status": stage.status,
        "records_processed": stage.records_processed,
        "errors": stage.errors
    }

def execute_gold_stage(silver_data: Any, aggregation_rules: Optional[Dict] = None) -> Dict:
    """
    Gold stage: Business-ready aggregated data.
    
    Args:
        silver_data: Data from silver stage
        aggregation_rules: Optional aggregation rules
        
    Returns:
        Stage execution result
    """
    stage = PipelineStage(
        stage_name="gold_aggregation",
        layer=DataLayer.GOLD,
        input_source="silver_storage",
        output_target="gold_storage",
        transformation="aggregate_and_enrich",
        status="running",
        started_at=datetime.utcnow()
    )
    
    try:
        # In a real implementation, this would:
        # 1. Aggregate data (e.g., by market, category)
        # 2. Enrich with calculated fields (scores, composites)
        # 3. Write to gold storage (e.g., Snowflake Gold tables)
        
        stage.records_processed = len(silver_data) if isinstance(silver_data, (list, dict)) else 1
        stage.status = "completed"
        stage.completed_at = datetime.utcnow()
    except Exception as e:
        stage.status = "failed"
        stage.errors.append(str(e))
        stage.completed_at = datetime.utcnow()
    
    _pipeline_runs.append(stage)
    
    return {
        "stage": stage.stage_name,
        "status": stage.status,
        "records_processed": stage.records_processed,
        "errors": stage.errors
    }

def get_pipeline_history(limit: int = 50) -> List[Dict]:
    """Get pipeline execution history."""
    runs = _pipeline_runs[-limit:]
    return [
        {
            "stage_name": r.stage_name,
            "layer": r.layer.value,
            "status": r.status,
            "records_processed": r.records_processed,
            "errors": r.errors,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None
        }
        for r in runs
    ]

def get_pipeline_summary() -> Dict:
    """Get pipeline summary statistics."""
    total = len(_pipeline_runs)
    if total == 0:
        return {
            "total_runs": 0,
            "by_layer": {},
            "by_status": {}
        }
    
    by_layer = defaultdict(lambda: {"total": 0, "completed": 0, "failed": 0})
    by_status = defaultdict(int)
    
    for run in _pipeline_runs:
        layer_stats = by_layer[run.layer.value]
        layer_stats["total"] += 1
        by_status[run.status] += 1
        if run.status == "completed":
            layer_stats["completed"] += 1
        elif run.status == "failed":
            layer_stats["failed"] += 1
    
    return {
        "total_runs": total,
        "by_layer": {k: dict(v) for k, v in by_layer.items()},
        "by_status": dict(by_status)
    }

