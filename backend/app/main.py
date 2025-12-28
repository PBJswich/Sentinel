from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError
from .routes import router
from .database import init_db

app = FastAPI(
    title="Cross-Commodity Signal API",
    description="Serves macro, fundamental, sentiment, and technical trading signals",
    version="0.1.0"
)

# Add response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    
    # Optionally start schedulers if enabled
    import os
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
