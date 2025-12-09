"""Main FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logger import configure_logging, get_logger
from src.api.routes import router, get_orchestrator
from src.services.cache_manager import CacheManager

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting application", version=settings.app_version)
    
    # Clear cache on startup (fresh start for each container restart)
    try:
        cache_manager = CacheManager()
        if cache_manager.enabled:
            cache_manager.clear_cache()  # Clear all scraper cache
            logger.info("Cache cleared on startup")
        else:
            logger.info("Cache not enabled, skipping cache clear")
    except Exception as e:
        logger.warning("Failed to clear cache on startup", error=str(e))
        # Continue startup even if cache clear fails
    
    # Initialize orchestrator
    orchestrator = get_orchestrator()
    await orchestrator.initialize()
    logger.info("Orchestrator initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await orchestrator.cleanup()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade website scraper for email extraction",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers
    )

