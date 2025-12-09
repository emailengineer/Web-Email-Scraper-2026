"""Orchestrator service that coordinates the scraping workflow."""

import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.patterns import CONTACT_PAGES
from src.services.url_processor import URLProcessor
from src.services.scraper import WebScraper
from src.services.email_extractor import EmailExtractor
from src.services.mx_validator import MXValidator
from src.services.cache_manager import CacheManager

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
            
            # Step 4: If no valid emails found, try contact pages
            logger.info("No valid emails on root, trying contact pages", domain=root_domain)
            
            # Limit pages to visit (accounting for root page already visited)
            pages_to_try = CONTACT_PAGES[:max_pages - 1]  # -1 because we already visited root
            
            # Check timeout before starting
            if time.time() - start_time > timeout:
                logger.warning("Timeout reached before starting contact pages", domain=root_domain)
                result["total_pages"] = len(result["pages_visited"])
                result["execution_time"] = time.time() - start_time
                return result
            
            # Build URLs for contact pages with mapping
            url_to_page_map = {}
            contact_urls = []
            for page in pages_to_try:
                contact_url = self.url_processor.build_url(base_url, page)
                url_to_page_map[contact_url] = page
                contact_urls.append(contact_url)
            
            # Scrape contact pages (concurrently if enabled)
            if settings.concurrent_scraping and len(contact_urls) > 1:
                # Check timeout before concurrent scraping
                if time.time() - start_time > timeout:
                    logger.warning("Timeout reached before concurrent scraping", domain=root_domain)
                    result["total_pages"] = len(result["pages_visited"])
                    result["execution_time"] = time.time() - start_time
                    return result
                
                logger.info("Scraping contact pages concurrently", count=len(contact_urls), domain=root_domain)
                scraping_results = await self.scraper.scrape_multiple(contact_urls)
            else:
                # Sequential scraping with timeout checks
                scraping_results = []
                for contact_url in contact_urls:
                    # Check timeout before each request
                    if time.time() - start_time > timeout:
                        logger.warning("Timeout reached during sequential scraping", domain=root_domain)
                        break
                    
                    page_result = await self.scraper.scrape_page(contact_url)
                    scraping_results.append(page_result)
                    
                    # Check timeout after each request
                    if time.time() - start_time > timeout:
                        logger.warning("Timeout reached after scraping page", domain=root_domain)
                        break
            
            # Process all results - track both successful and failed pages
            all_emails: Set[str] = set()
            found_valid_email = False
            
            # Create reverse mapping for easier lookup (normalize URLs for matching)
            normalized_url_to_page = {}
            for url, page in url_to_page_map.items():
                normalized_url = self.url_processor.normalize_url(url)
                normalized_url_to_page[normalized_url] = page
            
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
                if not page_path and i < len(pages_to_try):
                    page_path = pages_to_try[i]
                
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
                
                # Check timeout during processing
                if time.time() - start_time > timeout:
                    logger.warning("Timeout reached during result processing", domain=root_domain)
                    break
                
                # Extract emails from successful page
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
                            # Continue processing to find all emails, but we found at least one
                except Exception as e:
                    logger.warning("Email extraction failed", page=page_path, error=str(e))
                    continue
                
                # Check max pages limit
                if len(result["pages_visited"]) >= max_pages:
                    logger.info("Max pages reached", domain=root_domain, pages=len(result["pages_visited"]))
                    break
            
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
        
        Args:
            emails: Set of email addresses
            domain: Domain being scraped
            found_on: Page where emails were found
            
        Returns:
            List of validated email dictionaries
        """
        valid_emails = []
        
        # Filter emails by domain first
        domain_emails = {email for email in emails if email.endswith(f'@{domain}')}
        
        if not domain_emails:
            logger.debug("No emails matching domain", domain=domain)
            return valid_emails
        
        # Validate emails
        validation_results = self.mx_validator.validate_emails_batch(list(domain_emails))
        
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

