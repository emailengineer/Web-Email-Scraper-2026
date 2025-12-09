"""Tests for URL processor service."""

import pytest
from src.services.url_processor import URLProcessor
from src.utils.exceptions import InvalidURLException


def test_extract_root_domain():
    """Test root domain extraction."""
    processor = URLProcessor()
    
    assert processor.extract_root_domain("https://example.com") == "example.com"
    assert processor.extract_root_domain("https://www.example.com") == "example.com"
    assert processor.extract_root_domain("http://subdomain.example.com/path") == "example.com"
    
    with pytest.raises(InvalidURLException):
        processor.extract_root_domain("invalid-url")


def test_normalize_url():
    """Test URL normalization."""
    processor = URLProcessor()
    
    assert processor.normalize_url("example.com") == "https://example.com/"
    assert processor.normalize_url("https://example.com") == "https://example.com/"
    assert processor.normalize_url("https://EXAMPLE.COM/path") == "https://example.com/path"


def test_build_url():
    """Test URL building."""
    processor = URLProcessor()
    
    assert processor.build_url("https://example.com", "/contact") == "https://example.com/contact"
    assert processor.build_url("https://example.com/", "contact") == "https://example.com/contact"

