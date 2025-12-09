"""Orchestrator service that coordinates the scraping workflow."""

import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.patterns import CONTACT_PAGES
from src.utils.public_email_providers import is_valid_email_domain
from src.services.url_processor import URLProcessor
from src.services.scraper import WebScraper
from src.services.email_extractor import EmailExtractor
from src.services.mx_validator import MXValidator
from src.services.cache_manager import CacheManager
from src.services.link_discoverer import LinkDiscoverer

logger = get_logger(__name__)


class ScrapingOrchestrator:
    """Orchestrates the entire scraping workflow."""
    
    def __init__(self):
        """Initialize orchestrator with all required services."""
        self.url_processor = URLProcessor()
        self.scraper = WebScraper()
        self.email_extractor = EmailExtractor()
        self.cache_manager = CacheManager()
        self.mx_validator = MXValidator(self.cache_manager)
        self.link_discoverer = LinkDiscoverer()
    
    async def initialize(self) -> None:
        """Initialize services that require async setup."""
        await self.scraper.initialize_browser()
    
    async def scrape_website(self, url: str, max_pages: Optional[int] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Main method to scrape website and find emails.
        
        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to visit (optional)
            timeout: Timeout in seconds (optional)
            
        Returns:
            Dictionary with scraping results
        """
        start_time = time.time()
        max_pages = max_pages or settings.max_pages_to_visit
        timeout = timeout or settings.default_timeout
        
        result = {
            "success": False,
            "domain": None,
            "emails": [],
            "pages_visited": [],
            "total_pages": 0,
            "execution_time": 0.0,
            "error": None
        }
        
        try:
            # Step 1: Extract and normalize domain
            normalized_url = self.url_processor.normalize_url(url)
            root_domain = self.url_processor.extract_root_domain(normalized_url)
            base_url = self.url_processor.get_base_url(normalized_url)
            
            result["domain"] = root_domain
            logger.info("Starting website scrape", url=normalized_url, domain=root_domain)
            
            # Step 2: Check cache for known invalid domains
            if self.cache_manager.get_invalid_domain(root_domain):
                logger.info("Domain known to be invalid, skipping", domain=root_domain)
                result["success"] = True
                result["execution_time"] = time.time() - start_time
                return result
            
            # Step 3: Scrape root domain first
            logger.info("Scraping root domain", url=base_url)
            root_result = await self.scraper.scrape_page(base_url)
            
            # Always track root page as visited (even if failed)
            result["pages_visited"].append("/")
            
            if root_result["success"]:
                # Extract emails from root page
                try:
                    emails = self.email_extractor.extract_emails(root_result["html"], base_url)
                    
                    if emails:
                        logger.debug("Emails found on root page", count=len(emails), domain=root_domain)
                        # Validate emails
                        valid_emails = await self._validate_emails(emails, root_domain, "/")
                        
                        if valid_emails:
                            result["emails"] = valid_emails
                            result["success"] = True
                            result["total_pages"] = 1
                            result["execution_time"] = time.time() - start_time
                            logger.info("Valid emails found on root page", domain=root_domain, count=len(valid_emails))
                            return result
                except Exception as e:
                    logger.warning("Email extraction failed on root page", domain=root_domain, error=str(e))
            else:
                logger.warning("Root page scraping failed", domain=root_domain, error=root_result.get("error"))
            
            # Step 4: Discover links from homepage, sitemap, etc.
            logger.info("Discovering links from website", domain=root_domain)
            
            # Check timeout before link discovery
            if time.time() - start_time > timeout:
                logger.warning("Timeout reached before link discovery", domain=root_domain)
                result["total_pages"] = len(result["pages_visited"])
                result["execution_time"] = time.time() - start_time
                return result
            
            # Discover links from homepage, sitemap, robots.txt, SEO
            discovered_links = await self.link_discoverer.discover_links(base_url, root_domain)
            
            # Step 5: Build list of URLs to try (discovered links first, then fixed pages)
            url_to_page_map = {}
            urls_to_try = []
            discovered_urls = set()
            
            # Add discovered links first (they have higher priority)
            remaining_pages = max_pages - 1  # -1 for root page already visited
            for link_info in discovered_links[:remaining_pages]:
                link_url = link_info.get('url', '')
                link_path = link_info.get('path', '')
                
                if link_url and link_url not in url_to_page_map:
                    url_to_page_map[link_url] = link_path
                    urls_to_try.append(link_url)
                    discovered_urls.add(link_url)
                    remaining_pages -= 1
                    
                    if remaining_pages <= 0:
                        break
            
            # Add fixed contact pages as fallback (if we haven't reached max_pages)
            fixed_urls_count = 0
            if remaining_pages > 0:
                pages_to_try = CONTACT_PAGES[:remaining_pages]
                for page in pages_to_try:
                    contact_url = self.url_processor.build_url(base_url, page)
                    if contact_url not in url_to_page_map:
                        url_to_page_map[contact_url] = page
                        urls_to_try.append(contact_url)
                        fixed_urls_count += 1
            
            logger.info("URLs to scrape", 
                       discovered=len(discovered_urls),
                       fixed=fixed_urls_count,
                       total=len(urls_to_try),
                       domain=root_domain)
            
            # Check timeout before starting
            if time.time() - start_time > timeout:
                logger.warning("Timeout reached before starting page scraping", domain=root_domain)
                result["total_pages"] = len(result["pages_visited"])
                result["execution_time"] = time.time() - start_time
                return result
            
            # Scrape discovered and fixed pages (concurrently if enabled)
            # Always use concurrent scraping for better performance and to avoid race conditions
            if len(urls_to_try) > 0:
                # Check timeout before scraping
                if time.time() - start_time > timeout:
                    logger.warning("Timeout reached before scraping pages", domain=root_domain)
                    result["total_pages"] = len(result["pages_visited"])
                    result["execution_time"] = time.time() - start_time
                    return result
                
                # Use concurrent scraping for all pages (more reliable)
                logger.info("Scraping pages concurrently", count=len(urls_to_try), domain=root_domain)
                
                # Process in batches to avoid overwhelming the system
                batch_size = settings.max_concurrent_requests
                scraping_results = []
                
                for i in range(0, len(urls_to_try), batch_size):
                    # Check timeout before each batch
                    if time.time() - start_time > timeout:
                        logger.warning("Timeout reached before batch", domain=root_domain, batch=i//batch_size)
                        break
                    
                    batch_urls = urls_to_try[i:i + batch_size]
                    batch_results = await self.scraper.scrape_multiple(batch_urls)
                    scraping_results.extend(batch_results)
                    
                    # Check timeout after batch
                    if time.time() - start_time > timeout:
                        logger.warning("Timeout reached after batch", domain=root_domain)
                        break
            else:
                scraping_results = []
            
            # Process all results - track both successful and failed pages
            all_emails: Set[str] = set()
            found_valid_email = False
            
            # Create reverse mapping for easier lookup (normalize URLs for matching)
            normalized_url_to_page = {}
            for url, page in url_to_page_map.items():
                normalized_url = self.url_processor.normalize_url(url)
                normalized_url_to_page[normalized_url] = page
            
            # Process ALL results - don't break early
            total_results = len(scraping_results)
            logger.info("Processing scraping results", total=total_results, domain=root_domain)
            
            for i, page_result in enumerate(scraping_results):
                # Get the page path from URL mapping
                page_url = page_result.get("url", "")
                
                # Try to find page path from mapping (handle URL normalization)
                page_path = url_to_page_map.get(page_url)
                if not page_path:
                    # Try normalized URL
                    normalized_url = self.url_processor.normalize_url(page_url) if page_url else ""
                    page_path = normalized_url_to_page.get(normalized_url)
                
                # Fallback to index-based lookup if mapping fails
                if not page_path and i < len(urls_to_try):
                    # Try to extract path from URL
                    try:
                        parsed = urlparse(urls_to_try[i])
                        page_path = parsed.path or "/"
                    except Exception:
                        page_path = f"page_{i}"
                
                # Final fallback
                if not page_path:
                    page_path = f"page_{i}"
                    logger.warning("Could not map URL to page path", url=page_url, index=i)
                
                # Track all pages attempted (both successful and failed)
                if page_path not in result["pages_visited"]:
                    result["pages_visited"].append(page_path)
                
                # Skip processing if page scraping failed
                if not page_result["success"]:
                    logger.debug("Page scraping failed, skipping email extraction", 
                               page=page_path, error=page_result.get("error"))
                    continue
                
                # Extract emails from successful page (process all pages, don't break early)
                try:
                    page_emails = self.email_extractor.extract_emails(page_result["html"], page_result["url"])
                    all_emails.update(page_emails)
                    
                    # Validate emails found on this page
                    if page_emails:
                        valid_emails = await self._validate_emails(page_emails, root_domain, page_path)
                        
                        if valid_emails:
                            result["emails"].extend(valid_emails)
                            found_valid_email = True
                            logger.info("Valid emails found", domain=root_domain, page=page_path, count=len(valid_emails))
                            # Continue processing ALL pages to find all emails
                            
                except Exception as e:
                    logger.warning("Email extraction failed", page=page_path, error=str(e))
                    continue
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.debug("Processing progress", 
                               processed=i+1, 
                               total=total_results, 
                               domain=root_domain)
            
            # If we collected emails but haven't validated them all yet, validate now
            if all_emails and not found_valid_email:
                # Validate all collected emails
                all_valid_emails = await self._validate_emails(all_emails, root_domain, "multiple")
                result["emails"] = all_valid_emails
                result["success"] = len(all_valid_emails) > 0
            elif found_valid_email:
                # We already have validated emails, just mark success
                result["success"] = True
            
            result["total_pages"] = len(result["pages_visited"])
            result["execution_time"] = time.time() - start_time
            
            # Count successful vs failed pages
            successful_pages = sum(1 for r in scraping_results if r.get("success", False))
            failed_pages = len(scraping_results) - successful_pages
            
            logger.info("Scraping completed", 
                       domain=root_domain, 
                       pages_attempted=len(result["pages_visited"]),
                       pages_successful=successful_pages + (1 if root_result.get("success") else 0),
                       pages_failed=failed_pages + (0 if root_result.get("success") else 1),
                       emails_found=len(result["emails"]),
                       emails_extracted=len(all_emails),
                       execution_time=result["execution_time"])
            
        except Exception as e:
            logger.error("Scraping failed", url=url, error=str(e))
            result["error"] = str(e)
            result["success"] = False
            result["execution_time"] = time.time() - start_time
        
        return result
    
    async def _validate_emails(self, emails: Set[str], domain: str, found_on: str) -> List[Dict[str, Any]]:
        """
        Validate emails and return only those with valid MX records.
        Accepts emails from target domain OR public email providers.
        
        Args:
            emails: Set of email addresses
            domain: Domain being scraped
            found_on: Page where emails were found
            
        Returns:
            List of validated email dictionaries
        """
        valid_emails = []
        
        # Filter emails by domain (target domain OR public email providers)
        filtered_emails = set()
        for email in emails:
            if '@' not in email:
                continue
            
            email_domain = email.split('@')[1].lower()
            
            # Accept target domain or public email providers
            if is_valid_email_domain(email_domain, domain):
                filtered_emails.add(email)
        
        if not filtered_emails:
            logger.debug("No emails matching domain or public providers", 
                        domain=domain, 
                        total_emails=len(emails))
            return valid_emails
        
        logger.debug("Filtered emails for validation", 
                    domain=domain,
                    filtered=len(filtered_emails),
                    total=len(emails))
        
        # Validate emails (MX check will filter invalid ones)
        validation_results = self.mx_validator.validate_emails_batch(list(filtered_emails))
        
        for validation in validation_results:
            if validation["valid_format"] and validation["has_mx"]:
                valid_emails.append({
                    "email": validation["email"],
                    "domain": validation["domain"],
                    "mx_valid": True,
                    "found_on": found_on,
                    "mx_records": validation.get("mx_records", [])
                })
        
        return valid_emails
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.scraper.close()
        await self.link_discoverer.close()

