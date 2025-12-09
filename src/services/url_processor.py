"""URL processing and domain extraction."""

from urllib.parse import urlparse, urljoin, urlunparse
import tldextract
from typing import Optional

from src.utils.exceptions import InvalidURLException
from src.core.logger import get_logger

logger = get_logger(__name__)


class URLProcessor:
    """Handles URL normalization and domain extraction."""
    
    @staticmethod
    def extract_root_domain(url: str) -> str:
        """
        Extract root domain from URL.
        
        Args:
            url: Input URL
            
        Returns:
            Root domain (e.g., 'example.com')
            
        Raises:
            InvalidURLException: If URL is invalid
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # If no scheme, add https
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            
            # Extract domain using tldextract
            extracted = tldextract.extract(parsed.netloc or url)
            
            if not extracted.domain:
                raise InvalidURLException(f"Could not extract domain from URL: {url}")
            
            # Construct root domain
            root_domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
            
            logger.info("Extracted root domain", url=url, domain=root_domain)
            return root_domain.lower()
            
        except Exception as e:
            logger.error("Failed to extract root domain", url=url, error=str(e))
            raise InvalidURLException(f"Invalid URL: {url}") from e
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL to standard format.
        
        Args:
            url: Input URL
            
        Returns:
            Normalized URL
        """
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            parsed = urlparse(url)
            
            # Reconstruct with normalized components
            normalized = urlunparse((
                parsed.scheme or 'https',
                parsed.netloc.lower(),
                parsed.path.rstrip('/') or '/',
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize URL", url=url, error=str(e))
            raise InvalidURLException(f"Invalid URL: {url}") from e
    
    @staticmethod
    def build_url(base_url: str, path: str) -> str:
        """
        Build full URL from base URL and path.
        
        Args:
            base_url: Base URL
            path: Path to append
            
        Returns:
            Full URL
        """
        try:
            # Normalize base URL first
            base_url = URLProcessor.normalize_url(base_url)
            
            # Ensure path starts with /
            if not path.startswith('/'):
                path = f'/{path}'
            
            # Join URLs
            full_url = urljoin(base_url, path)
            
            return full_url
            
        except Exception as e:
            logger.error("Failed to build URL", base_url=base_url, path=path, error=str(e))
            raise InvalidURLException(f"Failed to build URL: {base_url}{path}") from e
    
    @staticmethod
    def get_base_url(url: str) -> str:
        """
        Get base URL (scheme + domain) from full URL.
        
        Args:
            url: Full URL
            
        Returns:
            Base URL (e.g., 'https://example.com')
        """
        try:
            parsed = urlparse(URLProcessor.normalize_url(url))
            base = f"{parsed.scheme}://{parsed.netloc}"
            return base
        except Exception as e:
            logger.error("Failed to get base URL", url=url, error=str(e))
            raise InvalidURLException(f"Invalid URL: {url}") from e

