"""
Scheduling logic for automated data updates.
"""

import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler = None
_orchestrator: PipelineOrchestrator = None


def get_orchestrator() -> PipelineOrchestrator:
    """Get or create pipeline orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


def ingest_daily_signals():
    """Ingest daily signals (technical and macro)."""
    logger.info("Starting daily signal ingestion...")
    orchestrator = get_orchestrator()
    
    # Ingest technical signals
    tech_result = orchestrator.ingest_technical_signals()
    logger.info(f"Technical signals: {tech_result.get('stored', 0)} stored")
    
    # Ingest macro signals
    macro_result = orchestrator.ingest_macro_signals()
    logger.info(f"Macro signals: {macro_result.get('stored', 0)} stored")
    
    return {
        'technical': tech_result,
        'macro': macro_result
    }


def ingest_energy_fundamentals():
    """Ingest weekly energy fundamentals (placeholder for EIA API)."""
    logger.info("Starting energy fundamentals ingestion...")
    # TODO: Implement EIA API adapter when ready
    logger.warning("Energy fundamentals ingestion not yet implemented (EIA API adapter needed)")
    return {'success': False, 'message': 'Not yet implemented'}


def setup_schedulers() -> BackgroundScheduler:
    """
    Set up automated schedulers for data ingestion.
    
    Returns:
        Configured scheduler instance
    """
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running")
        return _scheduler
    
    _scheduler = BackgroundScheduler()
    
    # Daily updates at market close (4:00 PM ET)
    _scheduler.add_job(
        ingest_daily_signals,
        trigger=CronTrigger(hour=16, minute=0, timezone='America/New_York'),
        id='daily_signals',
        name='Daily Signal Ingestion',
        replace_existing=True
    )
    
    # Weekly EIA update (Wednesdays at 10:30 AM ET - when EIA reports are released)
    _scheduler.add_job(
        ingest_energy_fundamentals,
        trigger=CronTrigger(day_of_week='wed', hour=10, minute=30, timezone='America/New_York'),
        id='weekly_energy',
        name='Weekly Energy Fundamentals',
        replace_existing=True
    )
    
    logger.info("Schedulers configured:")
    logger.info("  - Daily signals: 4:00 PM ET")
    logger.info("  - Weekly energy: Wednesday 10:30 AM ET")
    
    return _scheduler


def start_schedulers():
    """Start the schedulers."""
    scheduler = setup_schedulers()
    if not scheduler.running:
        scheduler.start()
        logger.info("Schedulers started")
    return scheduler


def stop_schedulers():
    """Stop the schedulers."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Schedulers stopped")

