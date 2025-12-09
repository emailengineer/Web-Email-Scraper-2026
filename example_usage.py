#!/usr/bin/env python3
"""
Example script demonstrating how to use the Website Scraper API.
"""

import requests
import json
import sys


def scrape_website(url: str, max_pages: int = 50, timeout: int = 30):
    """
    Scrape a website and extract emails.
    
    Args:
        url: Website URL to scrape
        max_pages: Maximum pages to visit
        timeout: Timeout in seconds
    """
    api_url = "http://localhost:8000/api/v1/scrape"
    
    payload = {
        "url": url,
        "max_pages": max_pages,
        "timeout": timeout
    }
    
    print(f"🔍 Scraping: {url}")
    print(f"📊 Max pages: {max_pages}, Timeout: {timeout}s")
    print("-" * 50)
    
    try:
        response = requests.post(api_url, json=payload, timeout=timeout + 10)
        response.raise_for_status()
        
        result = response.json()
        
        if result["success"]:
            print(f"✅ Success!")
            print(f"🌐 Domain: {result['domain']}")
            print(f"📄 Pages visited: {result['total_pages']}")
            print(f"⏱️  Execution time: {result['execution_time']:.2f}s")
            print(f"📧 Emails found: {len(result['emails'])}")
            print()
            
            if result["emails"]:
                print("📬 Valid Emails:")
                for email in result["emails"]:
                    print(f"   • {email['email']} (found on: {email['found_on']})")
            else:
                print("❌ No valid emails found")
            
            print()
            print("📋 Pages visited:")
            for page in result["pages_visited"]:
                print(f"   • {page}")
        else:
            print(f"❌ Scraping failed: {result.get('error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)


def check_health():
    """Check API health."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        response.raise_for_status()
        result = response.json()
        
        print("🏥 Health Check:")
        print(f"   Status: {result['status']}")
        print(f"   Version: {result['version']}")
        print(f"   Cache enabled: {result['cache_enabled']}")
        print(f"   Cache connected: {result['cache_connected']}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python example_usage.py <url> [max_pages] [timeout]")
        print("\nExample:")
        print("  python example_usage.py https://example.com")
        print("  python example_usage.py https://example.com 30 20")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    
    # Check health first
    if not check_health():
        print("\n⚠️  API may not be running. Start it with: docker-compose up -d")
        sys.exit(1)
    
    print()
    scrape_website(url, max_pages, timeout)

