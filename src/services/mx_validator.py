"""MX record validation service."""

import dns.resolver
import dns.exception
from typing import List, Optional, Dict, Any
from email_validator import validate_email, EmailNotValidError

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.exceptions import DNSValidationException
from src.services.cache_manager import CacheManager

logger = get_logger(__name__)


class MXValidator:
    """Validates email addresses by checking MX records."""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize MX validator.
        
        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = settings.dns_timeout
        self.resolver.lifetime = settings.dns_timeout
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validate email address format and MX records.
        
        Args:
            email: Email address to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "email": email.lower().strip(),
            "valid_format": False,
            "has_mx": False,
            "mx_records": [],
            "domain": None,
            "error": None
        }
        
        try:
            # Extract domain from email
            domain = email.split('@')[1] if '@' in email else None
            if not domain:
                result["error"] = "Invalid email format: no domain"
                return result
            
            result["domain"] = domain.lower()
            
            # Check cache first
            cached = self.cache_manager.get_mx_status(domain)
            if cached:
                result["valid_format"] = True
                result["has_mx"] = cached["has_mx"]
                result["mx_records"] = cached.get("mx_records", [])
                logger.debug("Using cached MX validation", email=email, has_mx=result["has_mx"])
                return result
            
            # Validate email format
            try:
                validated = validate_email(email, check_deliverability=False)
                result["valid_format"] = True
                result["email"] = validated.normalized
            except EmailNotValidError as e:
                result["error"] = f"Invalid email format: {str(e)}"
                return result
            
            # Check if domain is known to be invalid
            if self.cache_manager.get_invalid_domain(domain):
                result["has_mx"] = False
                logger.debug("Domain known to be invalid", domain=domain)
                return result
            
            # Check MX records
            mx_result = self.check_mx_records(domain)
            result["has_mx"] = mx_result["has_mx"]
            result["mx_records"] = mx_result["mx_records"]
            
            # Cache the result
            self.cache_manager.set_mx_status(
                domain,
                result["has_mx"],
                result["mx_records"]
            )
            
            # Mark as invalid if no MX records
            if not result["has_mx"]:
                self.cache_manager.mark_invalid_domain(domain)
            
            logger.info("Email validated", email=email, has_mx=result["has_mx"])
            
        except Exception as e:
            logger.error("Email validation failed", email=email, error=str(e))
            result["error"] = str(e)
        
        return result
    
    def check_mx_records(self, domain: str) -> Dict[str, Any]:
        """
        Check MX records for domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Dictionary with MX record information
        """
        result = {
            "has_mx": False,
            "mx_records": []
        }
        
        try:
            # Query MX records
            mx_records = self.resolver.resolve(domain, 'MX')
            
            if mx_records:
                result["has_mx"] = True
                result["mx_records"] = [
                    {
                        "preference": record.preference,
                        "exchange": str(record.exchange).rstrip('.')
                    }
                    for record in mx_records
                ]
                logger.debug("MX records found", domain=domain, count=len(result["mx_records"]))
            else:
                logger.debug("No MX records found", domain=domain)
                
        except dns.resolver.NXDOMAIN:
            logger.debug("Domain does not exist", domain=domain)
            result["has_mx"] = False
        except dns.resolver.NoAnswer:
            logger.debug("No MX records for domain", domain=domain)
            result["has_mx"] = False
        except dns.resolver.Timeout:
            logger.warning("DNS query timeout", domain=domain)
            result["has_mx"] = False
        except dns.exception.DNSException as e:
            logger.warning("DNS query failed", domain=domain, error=str(e))
            result["has_mx"] = False
        except Exception as e:
            logger.error("Unexpected error checking MX records", domain=domain, error=str(e))
            result["has_mx"] = False
        
        return result
    
    def validate_emails_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        """
        Validate multiple emails in batch.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of validation results
        """
        results = []
        for email in emails:
            result = self.validate_email(email)
            results.append(result)
        return results

