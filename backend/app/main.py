from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="Cross-Commodity Signal API",
    description="Serves macro, fundamental, sentiment, and technical trading signals",
    version="0.1.0"
)

app.include_router(router)
