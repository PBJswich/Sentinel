from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import time
from .routes import router
from .database import init_db
from .monitoring import record_request
from .rate_limit import rate_limit_middleware
from .redis_cache import init_redis

app = FastAPI(
    title="Cross-Commodity Signal API",
    description="Serves macro, fundamental, sentiment, and technical trading signals",
    version="0.1.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting middleware (if enabled)
if os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true":
    app.middleware("http")(rate_limit_middleware)

# Add monitoring middleware
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Record request metric
        record_request(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response

app.add_middleware(MonitoringMiddleware)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    
    # Initialize Redis if configured
    if os.getenv("REDIS_URL"):
        init_redis()
    
    # Optionally run initial data ingestion if database is empty
    if os.getenv("AUTO_INGEST_ON_STARTUP", "true").lower() == "true":
        from .database import SessionLocal
        from .db_service import get_all_signals_db
        
        # Check if database has signals
        db = SessionLocal()
        try:
            existing_signals = get_all_signals_db(db)
            if not existing_signals or len(existing_signals) == 0:
                # Database is empty, run initial ingestion
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Database is empty, running initial data ingestion...")
                
                from .pipeline.orchestrator import PipelineOrchestrator
                orchestrator = PipelineOrchestrator()
                result = orchestrator.run_full_pipeline()
                logger.info(f"Initial ingestion complete: {result.get('total_stored', 0)} signals stored")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not check database or run initial ingestion: {e}")
        finally:
            db.close()
    
    # Optionally start schedulers if enabled
    if os.getenv("ENABLE_SCHEDULERS", "false").lower() == "true":
        from .pipeline.schedulers import start_schedulers
        start_schedulers()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    from .pipeline.schedulers import stop_schedulers
    stop_schedulers()

app.include_router(router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with clean, readable responses."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "details": errors
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "details": errors
        }
    )
