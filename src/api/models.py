"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoint."""
    url: str = Field(..., description="Website URL to scrape")
    max_pages: Optional[int] = Field(None, ge=1, le=100, description="Maximum pages to visit")
    timeout: Optional[int] = Field(None, ge=5, le=300, description="Timeout in seconds")


class EmailResult(BaseModel):
    """Email result model."""
    email: str
    domain: str
    mx_valid: bool
    found_on: str
    mx_records: Optional[List[Dict[str, Any]]] = None


class ScrapeResponse(BaseModel):
    """Response model for scraping endpoint."""
    success: bool
    domain: Optional[str] = None
    emails: List[EmailResult] = []
    pages_visited: List[str] = []
    total_pages: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    cache_enabled: bool
    cache_connected: bool

