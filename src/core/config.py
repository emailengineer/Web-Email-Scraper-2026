"""Configuration management using Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Website Scraper"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Scraper
    default_timeout: int = 30
    page_load_timeout: int = 15
    max_concurrent_requests: int = 10
    max_pages_to_visit: int = 50
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # DNS
    dns_timeout: int = 5
    dns_retries: int = 3
    dns_cache_ttl: int = 86400
    
    # Cache
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_enabled: bool = True
    cache_ttl: int = 86400
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Performance
    enable_js_rendering: bool = True
    concurrent_scraping: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

