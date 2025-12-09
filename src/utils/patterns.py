"""Regex patterns for email extraction."""

import re
from typing import List, Pattern

# Comprehensive email regex patterns
EMAIL_PATTERNS: List[Pattern] = [
    # Standard email pattern
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    
    # Email with optional quotes
    re.compile(r'["\']?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})["\']?'),
    
    # Email in mailto: links
    re.compile(r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', re.IGNORECASE),
    
    # Email with obfuscation [at] and [dot]
    re.compile(r'\b([A-Za-z0-9._%+-]+)\s*\[?at\]?\s*([A-Za-z0-9.-]+)\s*\[?dot\]?\s*([A-Z|a-z]{2,})\b', re.IGNORECASE),
    
    # Email with (at) and (dot)
    re.compile(r'\b([A-Za-z0-9._%+-]+)\s*\(at\)\s*([A-Za-z0-9.-]+)\s*\(dot\)\s*([A-Z|a-z]{2,})\b', re.IGNORECASE),
    
    # Email with @ symbol obfuscated as (a) or [a]
    re.compile(r'\b([A-Za-z0-9._%+-]+)\s*[\(\[]a[\)\]]\s*([A-Za-z0-9.-]+)\s*\.\s*([A-Z|a-z]{2,})\b', re.IGNORECASE),
]

# Common contact page paths
CONTACT_PAGES = [
    # Contact pages
    '/contact',
    '/contact-us',
    '/contactus',
    '/contact_us',
    '/get-in-touch',
    '/reach-us',
    '/contact-information',
    '/contact.html',
    '/contact.php',
    
    # About pages
    '/about',
    '/about-us',
    '/aboutus',
    '/about_us',
    '/who-we-are',
    '/our-story',
    '/our-company',
    '/company',
    '/company-info',
    '/about.html',
    
    # Support pages
    '/support',
    '/help',
    '/customer-service',
    '/customer-support',
    '/customer-care',
    '/service',
    '/helpdesk',
    '/help-center',
    '/faq',
    '/frequently-asked-questions',
    '/contact-support',
    
    # Sales pages
    '/sales',
    '/sales-inquiry',
    '/request-quote',
    '/get-quote',
    '/quote',
    '/pricing',
    '/buy',
    '/purchase',
    '/order',
    '/wholesale',
    '/bulk-orders',
    '/b2b',
    '/business',
    '/enterprise',
    '/partner',
    '/partnerships',
    '/distributors',
    '/resellers',
    '/vendors',
]


def normalize_obfuscated_email(match: re.Match) -> str:
    """Convert obfuscated email patterns to standard format."""
    if len(match.groups()) == 1:
        return match.group(1).lower()
    
    # Handle [at] and [dot] patterns
    if len(match.groups()) == 3:
        local, domain, tld = match.groups()
        return f"{local.strip()}@{domain.strip()}.{tld.strip()}".lower()
    
    return match.group(0).lower()

