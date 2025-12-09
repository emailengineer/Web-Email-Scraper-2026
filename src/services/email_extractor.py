"""State-of-the-art email extraction service with comprehensive extraction methods."""

import re
from typing import Set, List
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from urllib.parse import unquote

from src.core.logger import get_logger
from src.utils.exceptions import EmailExtractionException
from src.utils.patterns import EMAIL_PATTERNS, normalize_obfuscated_email

logger = get_logger(__name__)


class EmailExtractor:
    """State-of-the-art email extractor that finds emails everywhere in HTML."""
    
    def __init__(self):
        """Initialize email extractor."""
        self.email_patterns = EMAIL_PATTERNS
        
        # Comprehensive email regex - more permissive since MX validation will filter
        self.comprehensive_email_pattern = re.compile(
            r'\b[A-Za-z0-9](?:[A-Za-z0-9._%+\-]*[A-Za-z0-9])?@[A-Za-z0-9](?:[A-Za-z0-9.\-]*[A-Za-z0-9])?\.[A-Za-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Additional patterns for edge cases
        self.edge_case_patterns = [
            # Emails with multiple dots
            re.compile(r'\b[\w.%+\-]+@[\w.%+\-]+\.[\w.%+\-]+\.[A-Za-z]{2,}\b', re.IGNORECASE),
            # Emails in quotes
            re.compile(r'["\']([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})["\']', re.IGNORECASE),
            # Emails with spaces (common in obfuscation)
            re.compile(r'\b([A-Za-z0-9._%+\-]+)\s*@\s*([A-Za-z0-9.\-]+)\s*\.\s*([A-Za-z]{2,})\b', re.IGNORECASE),
        ]
    
    def extract_emails(self, html_content: str, base_url: str = "") -> Set[str]:
        """
        Extract all email addresses from HTML content using comprehensive methods.
        
        Args:
            html_content: HTML content to extract from
            base_url: Base URL for context (optional)
            
        Returns:
            Set of unique email addresses found
        """
        emails: Set[str] = set()
        
        try:
            # Method 1: Extract from ALL text nodes (including hidden elements, footers, etc.)
            text_emails = self._extract_from_all_text_nodes(html_content)
            emails.update(text_emails)
            
            # Method 2: Extract from raw HTML (before parsing)
            raw_emails = self._extract_from_raw_html(html_content)
            emails.update(raw_emails)
            
            # Method 3: Extract from HTML attributes (comprehensive)
            attr_emails = self._extract_from_all_attributes(html_content)
            emails.update(attr_emails)
            
            # Method 4: Extract from comments
            comment_emails = self._extract_from_comments(html_content)
            emails.update(comment_emails)
            
            # Method 5: Extract from mailto links
            mailto_emails = self._extract_from_mailto(html_content)
            emails.update(mailto_emails)
            
            # Method 6: Extract obfuscated emails
            obfuscated_emails = self._extract_obfuscated(html_content)
            emails.update(obfuscated_emails)
            
            # Method 7: Extract from script tags (sometimes emails are in JS)
            script_emails = self._extract_from_scripts(html_content)
            emails.update(script_emails)
            
            # Method 8: Extract from style tags (rare but possible)
            style_emails = self._extract_from_styles(html_content)
            emails.update(style_emails)
            
            # Method 9: Extract from data attributes
            data_emails = self._extract_from_data_attributes(html_content)
            emails.update(data_emails)
            
            # Method 10: Extract from JSON-LD and structured data
            structured_emails = self._extract_from_structured_data(html_content)
            emails.update(structured_emails)
            
            # Clean and normalize emails (be lenient - MX validation will filter)
            cleaned_emails = self._clean_emails(emails)
            
            logger.info("Emails extracted", count=len(cleaned_emails), url=base_url)
            return cleaned_emails
            
        except Exception as e:
            logger.error("Email extraction failed", url=base_url, error=str(e))
            raise EmailExtractionException(f"Failed to extract emails: {str(e)}") from e
    
    def _extract_from_all_text_nodes(self, html_content: str) -> Set[str]:
        """Extract emails from ALL text nodes including hidden elements, footers, etc."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Get ALL text from the document, including hidden elements
            # This includes footers, headers, hidden divs, etc.
            all_text = soup.get_text(separator=' ', strip=False)
            
            # Extract emails from all text
            emails.update(self._extract_with_all_patterns(all_text))
            
            # Also extract from specific important sections
            # Footer (most common place for contact emails)
            footer = soup.find('footer')
            if footer:
                footer_text = footer.get_text(separator=' ', strip=False)
                emails.update(self._extract_with_all_patterns(footer_text))
            
            # Header
            header = soup.find('header')
            if header:
                header_text = header.get_text(separator=' ', strip=False)
                emails.update(self._extract_with_all_patterns(header_text))
            
            # All divs (including hidden ones with display:none, etc.)
            for div in soup.find_all('div'):
                div_text = div.get_text(separator=' ', strip=False)
                if div_text:
                    emails.update(self._extract_with_all_patterns(div_text))
            
            # All spans
            for span in soup.find_all('span'):
                span_text = span.get_text(separator=' ', strip=False)
                if span_text:
                    emails.update(self._extract_with_all_patterns(span_text))
            
            # All paragraphs
            for p in soup.find_all('p'):
                p_text = p.get_text(separator=' ', strip=False)
                if p_text:
                    emails.update(self._extract_with_all_patterns(p_text))
            
            # All list items
            for li in soup.find_all('li'):
                li_text = li.get_text(separator=' ', strip=False)
                if li_text:
                    emails.update(self._extract_with_all_patterns(li_text))
            
            # All table cells
            for td in soup.find_all(['td', 'th']):
                td_text = td.get_text(separator=' ', strip=False)
                if td_text:
                    emails.update(self._extract_with_all_patterns(td_text))
            
        except Exception as e:
            logger.warning("Failed to extract from text nodes", error=str(e))
        
        return emails
    
    def _extract_from_raw_html(self, html_content: str) -> Set[str]:
        """Extract emails directly from raw HTML before parsing."""
        emails: Set[str] = set()
        
        # Use comprehensive pattern on raw HTML
        emails.update(self._extract_with_all_patterns(html_content))
        
        return emails
    
    def _extract_from_all_attributes(self, html_content: str) -> Set[str]:
        """Extract emails from ALL HTML attributes."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Get all elements
            for element in soup.find_all(True):  # True means all tags
                # Check all attributes
                for attr_name, attr_value in element.attrs.items():
                    if isinstance(attr_value, list):
                        attr_value = ' '.join(str(v) for v in attr_value)
                    else:
                        attr_value = str(attr_value)
                    
                    # Extract emails from attribute value
                    if attr_value and '@' in attr_value:
                        emails.update(self._extract_with_all_patterns(attr_value))
        
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
                comment_text = str(comment)
                emails.update(self._extract_with_all_patterns(comment_text))
        
        except Exception as e:
            logger.warning("Failed to extract from comments", error=str(e))
        
        return emails
    
    def _extract_from_mailto(self, html_content: str) -> Set[str]:
        """Extract emails from mailto: links."""
        emails: Set[str] = set()
        
        try:
            # Find all mailto links
            mailto_pattern = re.compile(r'mailto:([^\s"\'<>]+)', re.IGNORECASE)
            matches = mailto_pattern.findall(html_content)
            
            for match in matches:
                email = unquote(match).strip()
                # Remove query parameters if any
                if '?' in email:
                    email = email.split('?')[0]
                emails.add(email.lower())
            
            # Also check href attributes specifically
            soup = BeautifulSoup(html_content, 'lxml')
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0].split('&')[0]
                    email = unquote(email).strip()
                    emails.add(email.lower())
        
        except Exception as e:
            logger.warning("Failed to extract from mailto", error=str(e))
        
        return emails
    
    def _extract_obfuscated(self, content: str) -> Set[str]:
        """Extract obfuscated emails with comprehensive patterns."""
        emails: Set[str] = set()
        
        try:
            # Common obfuscation patterns
            obfuscation_patterns = [
                # [at] and [dot]
                (re.compile(r'\b([A-Za-z0-9._%+\-]+)\s*\[at\]\s*([A-Za-z0-9.\-]+)\s*\[dot\]\s*([A-Za-z]{2,})\b', re.IGNORECASE),
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
                
                # (at) and (dot)
                (re.compile(r'\b([A-Za-z0-9._%+\-]+)\s*\(at\)\s*([A-Za-z0-9.\-]+)\s*\(dot\)\s*([A-Za-z]{2,})\b', re.IGNORECASE),
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
                
                # [a] pattern
                (re.compile(r'\b([A-Za-z0-9._%+\-]+)\s*\[a\]\s*([A-Za-z0-9.\-]+)\s*\.\s*([A-Za-z]{2,})\b', re.IGNORECASE),
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
                
                # AT and DOT
                (re.compile(r'\b([A-Za-z0-9._%+\-]+)\s+AT\s+([A-Za-z0-9.\-]+)\s+DOT\s+([A-Za-z]{2,})\b', re.IGNORECASE),
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
                
                # @ symbol replaced with words
                (re.compile(r'\b([A-Za-z0-9._%+\-]+)\s+(?:at|@)\s+([A-Za-z0-9.\-]+)\s+(?:dot|\.)\s+([A-Za-z]{2,})\b', re.IGNORECASE),
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3)}"),
            ]
            
            for pattern, converter in obfuscation_patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    try:
                        email = converter(match).lower().strip()
                        if self._is_valid_email_format(email):
                            emails.add(email)
                    except Exception:
                        continue
        
        except Exception as e:
            logger.warning("Failed to extract obfuscated emails", error=str(e))
        
        return emails
    
    def _extract_from_scripts(self, html_content: str) -> Set[str]:
        """Extract emails from script tags."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            scripts = soup.find_all('script')
            
            for script in scripts:
                script_text = script.string or ''
                emails.update(self._extract_with_all_patterns(script_text))
        
        except Exception as e:
            logger.warning("Failed to extract from scripts", error=str(e))
        
        return emails
    
    def _extract_from_styles(self, html_content: str) -> Set[str]:
        """Extract emails from style tags (rare but possible)."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            styles = soup.find_all('style')
            
            for style in styles:
                style_text = style.string or ''
                emails.update(self._extract_with_all_patterns(style_text))
        
        except Exception as e:
            logger.warning("Failed to extract from styles", error=str(e))
        
        return emails
    
    def _extract_from_data_attributes(self, html_content: str) -> Set[str]:
        """Extract emails from data-* attributes."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Find all elements with data attributes
            for element in soup.find_all(attrs=lambda x: x and any(k.startswith('data-') for k in x.keys())):
                for attr_name, attr_value in element.attrs.items():
                    if attr_name.startswith('data-') and isinstance(attr_value, str):
                        if '@' in attr_value:
                            emails.update(self._extract_with_all_patterns(attr_value))
        
        except Exception as e:
            logger.warning("Failed to extract from data attributes", error=str(e))
        
        return emails
    
    def _extract_from_structured_data(self, html_content: str) -> Set[str]:
        """Extract emails from JSON-LD and structured data."""
        emails: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # JSON-LD scripts
            for script in soup.find_all('script', type='application/ld+json'):
                if script.string:
                    script_text = script.string
                    emails.update(self._extract_with_all_patterns(script_text))
            
            # Microdata
            for element in soup.find_all(attrs={'itemprop': True}):
                itemprop_value = element.get('itemprop', '')
                if 'email' in itemprop_value.lower():
                    text = element.get_text() or element.get('content', '')
                    emails.update(self._extract_with_all_patterns(text))
        
        except Exception as e:
            logger.warning("Failed to extract from structured data", error=str(e))
        
        return emails
    
    def _extract_with_all_patterns(self, text: str) -> Set[str]:
        """Extract emails using all available patterns."""
        emails: Set[str] = set()
        
        if not text or '@' not in text:
            return emails
        
        # Use comprehensive pattern
        matches = self.comprehensive_email_pattern.findall(text)
        for match in matches:
            email = match.lower().strip()
            if self._is_valid_email_format(email):
                emails.add(email)
        
        # Use edge case patterns
        for pattern in self.edge_case_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Reconstruct email from groups
                    email = ''.join(match).lower().strip()
                else:
                    email = match.lower().strip()
                
                if self._is_valid_email_format(email):
                    emails.add(email)
        
        # Use standard patterns
        for pattern in EMAIL_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    email = ''.join(match).lower().strip()
                else:
                    email = match.lower().strip()
                
                if self._is_valid_email_format(email):
                    emails.add(email)
        
        return emails
    
    def _clean_emails(self, emails: Set[str]) -> Set[str]:
        """Clean and normalize email addresses (lenient - MX validation will filter)."""
        cleaned: Set[str] = set()
        
        for email in emails:
            if not email:
                continue
            
            # Remove common prefixes/suffixes
            email = email.strip()
            email = email.rstrip('.,;:!?)]}>')
            email = email.lstrip('([{<')
            email = email.lstrip('mailto:')
            
            # Remove quotes and brackets
            email = email.strip('"\'[](){}<>')
            
            # Remove trailing punctuation that might have been captured
            while email and email[-1] in '.,;:!?)]}>':
                email = email[:-1]
            
            # Basic format check (lenient - MX will validate)
            if '@' in email and '.' in email.split('@')[1] if '@' in email else False:
                cleaned.add(email.lower())
        
        return cleaned
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation (lenient - MX validation will filter false positives)."""
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
        
        # Basic checks (lenient)
        if not local or len(local) > 64:
            return False
        
        if not domain or '.' not in domain:
            return False
        
        # Check for valid TLD (at least 2 chars)
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False
        
        tld = domain_parts[-1]
        if len(tld) < 2:
            return False
        
        # Very basic character check (allow more since MX will validate)
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-%]+\.', email):
            return False
        
        return True
