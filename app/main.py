"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1.endpoints import router as v1_router

# Setup logging
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservice for automated legal analysis of immigration cases",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(v1_router, prefix="/v1", tags=["v1"])


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Project ID: {settings.PROJECT_ID}")
    logger.info(f"Location: {settings.LOCATION}")
    logger.info(f"Debug mode: {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.APP_NAME}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG
    )
