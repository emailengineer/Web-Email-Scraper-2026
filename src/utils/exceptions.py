"""Custom exceptions for the scraper application."""


class ScraperException(Exception):
    """Base exception for scraper errors."""
    pass


class InvalidURLException(ScraperException):
    """Raised when URL is invalid."""
    pass


class ScrapingException(ScraperException):
    """Raised when scraping fails."""
    pass


class EmailExtractionException(ScraperException):
    """Raised when email extraction fails."""
    pass


class DNSValidationException(ScraperException):
    """Raised when DNS validation fails."""
    pass


class CacheException(ScraperException):
    """Raised when cache operations fail."""
    pass

