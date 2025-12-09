"""API routes for the scraper application."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from src.core.config import settings
from src.core.logger import get_logger
from src.api.models import ScrapeRequest, ScrapeResponse, HealthResponse
from src.services.orchestrator import ScrapingOrchestrator
from src.services.cache_manager import CacheManager

logger = get_logger(__name__)
router = APIRouter()

# Global orchestrator instance (initialized on startup)
orchestrator: ScrapingOrchestrator = None
cache_manager: CacheManager = None


def get_orchestrator() -> ScrapingOrchestrator:
    """Get or create orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        orchestrator = ScrapingOrchestrator()
    return orchestrator


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    
    cache_connected = False
    if cache_manager.enabled and cache_manager.redis_client:
        try:
            cache_manager.redis_client.ping()
            cache_connected = True
        except Exception:
            pass
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        cache_enabled=cache_manager.enabled,
        cache_connected=cache_connected
    )


@router.post("/api/v1/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape website and extract emails.
    
    Args:
        request: Scrape request with URL and optional parameters
        
    Returns:
        Scrape response with found emails and metadata
    """
    try:
        logger.info("Scrape request received", url=request.url, max_pages=request.max_pages)
        
        # Get orchestrator
        orch = get_orchestrator()
        
        # Initialize if needed
        if not hasattr(orch, '_initialized'):
            await orch.initialize()
            orch._initialized = True
        
        # Perform scraping
        result = await orch.scrape_website(
            url=request.url,
            max_pages=request.max_pages,
            timeout=request.timeout
        )
        
        # Convert to response model
        response = ScrapeResponse(
            success=result["success"],
            domain=result.get("domain"),
            emails=result.get("emails", []),
            pages_visited=result.get("pages_visited", []),
            total_pages=result.get("total_pages", 0),
            execution_time=result.get("execution_time", 0.0),
            error=result.get("error")
        )
        
        logger.info("Scrape request completed", 
                   url=request.url,
                   success=response.success,
                   emails_found=len(response.emails),
                   pages=response.total_pages)
        
        return response
        
    except Exception as e:
        logger.error("Scrape request failed", url=request.url, error=str(e))
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/api/v1/stats")
async def get_stats() -> Dict[str, Any]:
    """Get application statistics."""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    
    stats = {
        "version": settings.app_version,
        "cache_enabled": cache_manager.enabled,
        "cache_connected": False
    }
    
    if cache_manager.enabled and cache_manager.redis_client:
        try:
            cache_manager.redis_client.ping()
            stats["cache_connected"] = True
            
            # Get cache stats
            pattern = "scraper:*"
            keys = cache_manager.redis_client.keys(pattern)
            stats["cache_keys"] = len(keys) if keys else 0
        except Exception:
            pass
    
    return stats

