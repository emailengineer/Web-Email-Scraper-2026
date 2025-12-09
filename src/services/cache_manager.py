"""Cache manager for MX records."""

import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.exceptions import CacheException

logger = get_logger(__name__)


class CacheManager:
    """Manages caching of MX records and validation results."""
    
    def __init__(self):
        """Initialize cache manager with Redis connection."""
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.cache_enabled
        
        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected", host=settings.redis_host, port=settings.redis_port)
            except Exception as e:
                logger.warning("Redis cache unavailable, continuing without cache", error=str(e))
                self.enabled = False
                self.redis_client = None
    
    def _get_key(self, domain: str, key_type: str = "mx") -> str:
        """Generate cache key."""
        return f"scraper:{key_type}:{domain.lower()}"
    
    def get_mx_status(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get cached MX record status for domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Cached MX status or None if not cached
        """
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            key = self._get_key(domain, "mx")
            cached = self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                logger.debug("Cache hit for MX status", domain=domain)
                return data
            
            logger.debug("Cache miss for MX status", domain=domain)
            return None
            
        except Exception as e:
            logger.warning("Failed to get from cache", domain=domain, error=str(e))
            return None
    
    def set_mx_status(self, domain: str, has_mx: bool, mx_records: Optional[list] = None) -> None:
        """
        Cache MX record status for domain.
        
        Args:
            domain: Domain to cache
            has_mx: Whether domain has MX records
            mx_records: List of MX records (optional)
        """
        if not self.enabled or not self.redis_client:
            return
        
        try:
            key = self._get_key(domain, "mx")
            data = {
                "domain": domain.lower(),
                "has_mx": has_mx,
                "mx_records": mx_records or [],
                "cached_at": str(timedelta(seconds=0))
            }
            
            # Cache for TTL seconds
            self.redis_client.setex(
                key,
                settings.cache_ttl,
                json.dumps(data)
            )
            
            logger.debug("Cached MX status", domain=domain, has_mx=has_mx)
            
        except Exception as e:
            logger.warning("Failed to set cache", domain=domain, error=str(e))
    
    def get_invalid_domain(self, domain: str) -> bool:
        """
        Check if domain is known to be invalid (no MX records).
        
        Args:
            domain: Domain to check
            
        Returns:
            True if domain is known to be invalid
        """
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            key = self._get_key(domain, "invalid")
            exists = self.redis_client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.warning("Failed to check invalid domain cache", domain=domain, error=str(e))
            return False
    
    def mark_invalid_domain(self, domain: str) -> None:
        """
        Mark domain as invalid (no MX records).
        
        Args:
            domain: Domain to mark as invalid
        """
        if not self.enabled or not self.redis_client:
            return
        
        try:
            key = self._get_key(domain, "invalid")
            # Cache invalid domains for longer (7 days)
            self.redis_client.setex(key, 604800, "1")
            logger.debug("Marked domain as invalid", domain=domain)
        except Exception as e:
            logger.warning("Failed to mark invalid domain", domain=domain, error=str(e))
    
    def clear_cache(self, domain: Optional[str] = None, clear_all_redis: bool = False) -> None:
        """
        Clear cache for domain or all cache.
        
        Args:
            domain: Domain to clear, or None to clear all scraper cache
            clear_all_redis: If True, clear entire Redis database (use with caution)
        """
        if not self.enabled or not self.redis_client:
            return
        
        try:
            if clear_all_redis:
                # Clear entire Redis database
                self.redis_client.flushdb()
                logger.info("Cleared entire Redis database")
            elif domain:
                keys = [
                    self._get_key(domain, "mx"),
                    self._get_key(domain, "invalid")
                ]
                for key in keys:
                    self.redis_client.delete(key)
                logger.info("Cleared cache for domain", domain=domain)
            else:
                # Clear all scraper cache
                pattern = "scraper:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("Cleared all scraper cache", keys_deleted=len(keys) if keys else 0)
        except Exception as e:
            logger.error("Failed to clear cache", domain=domain, error=str(e))
            raise CacheException(f"Failed to clear cache: {str(e)}") from e

