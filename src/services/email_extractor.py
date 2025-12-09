"""Email extraction service with multiple extraction methods."""

import re
from typing import Set, List
from bs4 import BeautifulSoup, Comment
from urllib.parse import unquote

from src.core.logger import get_logger
from src.utils.exceptions import EmailExtractionException
from src.utils.patterns import EMAIL_PATTERNS, normalize_obfuscated_email

logger = get_logger(__name__)


class EmailExtractor:
    """Extracts email addresses from HTML content using multiple methods."""
    
    def __init__(self):
        """Initialize email extractor."""
        self.email_patterns = EMAIL_PATTERNS
    
    def extract_emails(self, html_content: str, base_url: str = "") -> Set[str]:
        """
        Extract all email addresses from HTML content.
        
        Args:
            html_content: HTML content to extract from
            base_url: Base URL for context (optional)
            
        Returns:
            Set of unique email addresses found
        """
        emails: Set[str] = set()
        
        try:
            # Method 1: Extract from plain text using regex
            text_emails = self._extract_from_text(html_content)
            emails.update(text_emails)
            
            # Method 2: Extract from HTML attributes
            attr_emails = self._extract_from_attributes(html_content)
            emails.update(attr_emails)
            
            # Method 3: Extract from comments
            comment_emails = self._extract_from_comments(html_content)
            emails.update(comment_emails)
            
            # Method 4: Extract from mailto links
            mailto_emails = self._extract_from_mailto(html_content)
            emails.update(mailto_emails)
            
            # Method 5: Extract obfuscated emails
            obfuscated_emails = self._extract_obfuscated(html_content)
            emails.update(obfuscated_emails)
            
            # Clean and normalize emails
            cleaned_emails = self._clean_emails(emails)
            
            logger.info("Emails extracted", count=len(cleaned_emails), url=base_url)
            return cleaned_emails
            
        except Exception as e:
            logger.error("Email extraction failed", url=base_url, error=str(e))
            raise EmailExtractionException(f"Failed to extract emails: {str(e)}") from e
    
    def _extract_from_text(self, content: str) -> Set[str]:
        """Extract emails from plain text using regex patterns."""
        emails: Set[str] = set()
        
        # Use first pattern (most common)
        pattern = EMAIL_PATTERNS[0]
        matches = pattern.findall(content)
        
        for match in matches:
            if isinstance(match, tuple):
                email = ''.join(match).lower().strip()
            else:
                email = match.lower().strip()
            
            if self._is_valid_email_format(email):
                emails.add(email)
        
        return emails
    
    def _extract_from_attributes(self, html_content: str) -> Set[str]:
        """Extract emails from HTML attributes."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Check common attributes that might contain emails
            attrs_to_check = ['href', 'data-email', 'data-contact', 'title', 'alt', 'value']
            
            for attr in attrs_to_check:
                elements = soup.find_all(attrs={attr: re.compile(r'@', re.IGNORECASE)})
                for element in elements:
                    attr_value = element.get(attr, '')
                    pattern = EMAIL_PATTERNS[0]
                    matches = pattern.findall(attr_value)
                    for match in matches:
                        email = (match if isinstance(match, str) else ''.join(match)).lower().strip()
                        if self._is_valid_email_format(email):
                            emails.add(email)
        
        except Exception as e:
            logger.warning("Failed to extract from attributes", error=str(e))
        
        return emails
    
    def _extract_from_comments(self, html_content: str) -> Set[str]:
        """Extract emails from HTML comments."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            
            for comment in comments:
                pattern = EMAIL_PATTERNS[0]
                matches = pattern.findall(str(comment))
                for match in matches:
                    email = (match if isinstance(match, str) else ''.join(match)).lower().strip()
                    if self._is_valid_email_format(email):
                        emails.add(email)
        
        except Exception as e:
            logger.warning("Failed to extract from comments", error=str(e))
        
        return emails
    
    def _extract_from_mailto(self, html_content: str) -> Set[str]:
        """Extract emails from mailto: links."""
        emails: Set[str] = set()
        
        try:
            pattern = EMAIL_PATTERNS[2]  # mailto pattern
            matches = pattern.findall(html_content, re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    email = ''.join(match).lower().strip()
                else:
                    email = match.lower().strip()
                
                # Decode URL encoding
                email = unquote(email)
                
                if self._is_valid_email_format(email):
                    emails.add(email)
        
        except Exception as e:
            logger.warning("Failed to extract from mailto", error=str(e))
        
        return emails
    
    def _extract_obfuscated(self, content: str) -> Set[str]:
        """Extract obfuscated emails (e.g., user[at]domain[dot]com)."""
        emails: Set[str] = set()
        
        try:
            # Check for [at] and [dot] patterns
            obfuscated_patterns = [
                EMAIL_PATTERNS[3],  # [at] and [dot]
                EMAIL_PATTERNS[4],  # (at) and (dot)
                EMAIL_PATTERNS[5],  # [a] pattern
            ]
            
            for pattern in obfuscated_patterns:
                matches = pattern.finditer(content, re.IGNORECASE)
                for match in matches:
                    try:
                        email = normalize_obfuscated_email(match)
                        if self._is_valid_email_format(email):
                            emails.add(email)
                    except Exception:
                        continue
        
        except Exception as e:
            logger.warning("Failed to extract obfuscated emails", error=str(e))
        
        return emails
    
    def _clean_emails(self, emails: Set[str]) -> Set[str]:
        """Clean and normalize email addresses."""
        cleaned: Set[str] = set()
        
        for email in emails:
            # Remove common prefixes/suffixes
            email = email.strip()
            email = email.rstrip('.,;:')
            email = email.lstrip('mailto:')
            
            # Remove quotes
            email = email.strip('"\'')
            
            # Basic validation
            if self._is_valid_email_format(email):
                cleaned.add(email.lower())
        
        return cleaned
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation."""
        if not email or len(email) < 5:
            return False
        
        # Must contain @
        if '@' not in email:
            return False
        
        # Split and check parts
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        
        # Local part validation
        if not local or len(local) > 64:
            return False
        
        # Domain validation
        if not domain or '.' not in domain:
            return False
        
        # Check for valid TLD
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False
        
        tld = domain_parts[-1]
        if len(tld) < 2 or len(tld) > 63:
            return False
        
        # Basic character check
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        return True

