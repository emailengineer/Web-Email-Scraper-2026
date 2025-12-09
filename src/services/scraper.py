"""Web scraping service using Playwright and httpx."""

import asyncio
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
import httpx
from bs4 import BeautifulSoup

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.exceptions import ScrapingException

logger = get_logger(__name__)


class WebScraper:
    """Web scraper with JavaScript rendering support."""
    
    def __init__(self):
        """Initialize web scraper."""
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.http_client = httpx.AsyncClient(
            timeout=settings.page_load_timeout,
            follow_redirects=True,
            headers={
                'User-Agent': settings.user_agent
            }
        )
        self._browser_initialized = False
    
    async def initialize_browser(self) -> None:
        """Initialize Playwright browser if JS rendering is enabled."""
        if not settings.enable_js_rendering:
            return
        
        if self._browser_initialized:
            return
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self._browser_initialized = True
            logger.info("Browser initialized for JS rendering")
        except Exception as e:
            logger.warning("Failed to initialize browser, falling back to HTTP", error=str(e))
            self._browser_initialized = False
    
    async def close_browser(self) -> None:
        """Close browser and cleanup."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        
        self._browser_initialized = False
    
    async def scrape_page(self, url: str, use_js: Optional[bool] = None) -> Dict[str, Any]:
        """
        Scrape a web page and return HTML content.
        
        Args:
            url: URL to scrape
            use_js: Whether to use JavaScript rendering (overrides config)
            
        Returns:
            Dictionary with HTML content and metadata
        """
        use_js = use_js if use_js is not None else settings.enable_js_rendering
        
        result = {
            "url": url,
            "html": "",
            "status_code": 0,
            "success": False,
            "error": None
        }
        
        try:
            # Try JavaScript rendering first if enabled
            if use_js and self._browser_initialized:
                try:
                    html = await self._scrape_with_playwright(url)
                    result["html"] = html
                    result["success"] = True
                    result["status_code"] = 200
                    logger.debug("Page scraped with Playwright", url=url)
                    return result
                except Exception as e:
                    logger.warning("Playwright scraping failed, falling back to HTTP", url=url, error=str(e))
            
            # Fallback to HTTP request
            html = await self._scrape_with_http(url)
            result["html"] = html
            result["success"] = True
            result["status_code"] = 200
            logger.debug("Page scraped with HTTP", url=url)
            
        except Exception as e:
            logger.error("Page scraping failed", url=url, error=str(e))
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    async def _scrape_with_playwright(self, url: str) -> str:
        """Scrape page using Playwright (JavaScript rendering)."""
        if not self.browser:
            await self.initialize_browser()
        
        if not self.browser:
            raise ScrapingException("Browser not available")
        
        page: Page = await self.browser.new_page()
        
        try:
            # Set user agent
            await page.set_extra_http_headers({
                'User-Agent': settings.user_agent
            })
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle', timeout=settings.page_load_timeout * 1000)
            
            # Get HTML content
            html = await page.content()
            
            return html
            
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout", url=url)
            # Return partial content if available
            try:
                html = await page.content()
                return html
            except Exception:
                raise ScrapingException(f"Timeout loading page: {url}")
        except Exception as e:
            raise ScrapingException(f"Playwright scraping failed: {str(e)}")
        finally:
            await page.close()
    
    async def _scrape_with_http(self, url: str) -> str:
        """Scrape page using HTTP request."""
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.TimeoutException:
            raise ScrapingException(f"Request timeout: {url}")
        except httpx.HTTPStatusError as e:
            raise ScrapingException(f"HTTP error {e.response.status_code}: {url}")
        except Exception as e:
            raise ScrapingException(f"HTTP request failed: {str(e)}")
    
    async def scrape_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraping results
        """
        if settings.concurrent_scraping and len(urls) > 1:
            tasks = [self.scrape_page(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("Scraping task failed", url=urls[i], error=str(result))
                    processed_results.append({
                        "url": urls[i],
                        "html": "",
                        "status_code": 0,
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        else:
            # Sequential scraping
            results = []
            for url in urls:
                result = await self.scrape_page(url)
                results.append(result)
            return results
    
    async def close(self) -> None:
        """Close HTTP client and browser."""
        await self.close_browser()
        await self.http_client.aclose()

