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
            
            if root_result["success"]:
                result["pages_visited"].append("/")
                
                # Extract emails from root page
                emails = self.email_extractor.extract_emails(root_result["html"], base_url)
                
                if emails:
                    # Validate emails
                    valid_emails = await self._validate_emails(emails, root_domain, "/")
                    
                    if valid_emails:
                        result["emails"] = valid_emails
                        result["success"] = True
                        result["total_pages"] = 1
                        result["execution_time"] = time.time() - start_time
                        logger.info("Valid emails found on root page", domain=root_domain, count=len(valid_emails))
                        return result
            
            # Step 4: If no valid emails found, try contact pages
            logger.info("No valid emails on root, trying contact pages", domain=root_domain)
            
            # Limit pages to visit
            pages_to_try = CONTACT_PAGES[:max_pages - 1]  # -1 because we already visited root
            
            # Build URLs for contact pages
            contact_urls = [
                self.url_processor.build_url(base_url, page)
                for page in pages_to_try
            ]
            
            # Scrape contact pages (concurrently if enabled)
            if settings.concurrent_scraping:
                scraping_results = await self.scraper.scrape_multiple(contact_urls)
            else:
                scraping_results = []
                for contact_url in contact_urls:
                    if time.time() - start_time > timeout:
                        logger.warning("Timeout reached, stopping scraping", domain=root_domain)
                        break
                    
                    page_result = await self.scraper.scrape_page(contact_url)
                    scraping_results.append(page_result)
            
            # Process results
            all_emails: Set[str] = set()
            
            for i, page_result in enumerate(scraping_results):
                if not page_result["success"]:
                    continue
                
                page_path = CONTACT_PAGES[i]
                result["pages_visited"].append(page_path)
                
                # Extract emails
                page_emails = self.email_extractor.extract_emails(page_result["html"], page_result["url"])
                all_emails.update(page_emails)
                
                # Validate emails found on this page
                if page_emails:
                    valid_emails = await self._validate_emails(page_emails, root_domain, page_path)
                    
                    if valid_emails:
                        result["emails"].extend(valid_emails)
                        result["success"] = True
                        result["total_pages"] = len(result["pages_visited"])
                        result["execution_time"] = time.time() - start_time
                        logger.info("Valid emails found", domain=root_domain, page=page_path, count=len(valid_emails))
                        return result
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning("Timeout reached", domain=root_domain)
                    break
                
                # Check max pages
                if len(result["pages_visited"]) >= max_pages:
                    logger.info("Max pages reached", domain=root_domain)
                    break
            
            # If we have emails but none validated, still return them
            if all_emails:
                # Validate all collected emails
                all_valid_emails = await self._validate_emails(all_emails, root_domain, "multiple")
                result["emails"] = all_valid_emails
                result["success"] = len(all_valid_emails) > 0
            
            result["total_pages"] = len(result["pages_visited"])
            result["execution_time"] = time.time() - start_time
            
            logger.info("Scraping completed", 
                       domain=root_domain, 
                       pages=result["total_pages"],
                       emails_found=len(result["emails"]),
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

