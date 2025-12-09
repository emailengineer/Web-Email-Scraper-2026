"""Link discovery service for finding relevant pages on a website."""

import re
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import httpx
import asyncio

from src.core.config import settings
from src.core.logger import get_logger
from src.utils.exceptions import ScrapingException
from src.services.url_processor import URLProcessor

logger = get_logger(__name__)


class LinkDiscoverer:
    """Discovers links, sitemaps, and relevant pages from a website."""
    
    def __init__(self):
        """Initialize link discoverer."""
        self.url_processor = URLProcessor()
        self.http_client = httpx.AsyncClient(
            timeout=settings.page_load_timeout,
            follow_redirects=True,
            headers={'User-Agent': settings.user_agent}
        )
        
        # Keywords that indicate contact/about/support pages
        self.relevant_keywords = {
            'contact', 'about', 'support', 'help', 'sales', 'team',
            'company', 'reach', 'connect', 'inquiry', 'quote', 'pricing',
            'service', 'customer', 'faq', 'business', 'enterprise', 'partner'
        }
    
    async def discover_links(self, base_url: str, root_domain: str) -> List[Dict[str, Any]]:
        """
        Discover all relevant links from a website.
        
        Args:
            base_url: Base URL of the website
            root_domain: Root domain for filtering
            
        Returns:
            List of discovered links with metadata
        """
        discovered_links: List[Dict[str, Any]] = []
        
        try:
            # Step 1: Discover from homepage
            homepage_links = await self._discover_from_homepage(base_url, root_domain)
            discovered_links.extend(homepage_links)
            
            # Step 2: Discover from sitemap
            sitemap_links = await self._discover_from_sitemap(base_url, root_domain)
            discovered_links.extend(sitemap_links)
            
            # Step 3: Discover from robots.txt
            robots_links = await self._discover_from_robots(base_url, root_domain)
            discovered_links.extend(robots_links)
            
            # Step 4: Discover from SEO meta tags
            seo_links = await self._discover_from_seo(base_url, root_domain)
            discovered_links.extend(seo_links)
            
            # Deduplicate and prioritize
            unique_links = self._deduplicate_and_prioritize(discovered_links, root_domain)
            
            logger.info("Links discovered", 
                       total=len(discovered_links),
                       unique=len(unique_links),
                       domain=root_domain)
            
            return unique_links
            
        except Exception as e:
            logger.error("Link discovery failed", domain=root_domain, error=str(e))
            return []
    
    async def _discover_from_homepage(self, base_url: str, root_domain: str) -> List[Dict[str, Any]]:
        """Discover links from homepage HTML."""
        links: List[Dict[str, Any]] = []
        
        try:
            response = await self.http_client.get(base_url)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            
            # Find all <a> tags
            for tag in soup.find_all('a', href=True):
                href = tag.get('href', '').strip()
                if not href or href.startswith('#'):
                    continue
                
                link_info = self._process_link(href, base_url, root_domain, tag)
                if link_info:
                    links.append(link_info)
            
            # Find buttons and other elements with onclick or data attributes
            for button in soup.find_all(['button', 'div', 'span'], 
                                       onclick=True, 
                                       class_=re.compile(r'contact|about|support|help', re.I)):
                onclick = button.get('onclick', '')
                href = self._extract_url_from_onclick(onclick)
                if href:
                    link_info = self._process_link(href, base_url, root_domain, button)
                    if link_info:
                        links.append(link_info)
            
            # Find links in data attributes
            for elem in soup.find_all(attrs={'data-href': True}):
                href = elem.get('data-href', '').strip()
                if href:
                    link_info = self._process_link(href, base_url, root_domain, elem)
                    if link_info:
                        links.append(link_info)
            
            logger.debug("Links found on homepage", count=len(links), domain=root_domain)
            
        except Exception as e:
            logger.warning("Failed to discover links from homepage", domain=root_domain, error=str(e))
        
        return links
    
    async def _discover_from_sitemap(self, base_url: str, root_domain: str) -> List[Dict[str, Any]]:
        """Discover links from sitemap.xml."""
        links: List[Dict[str, Any]] = []
        
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap1.xml",
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = await self.http_client.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # Parse XML sitemap
                    soup = BeautifulSoup(content, 'xml')
                    
                    # Find all <loc> tags (sitemap format)
                    for loc in soup.find_all('loc'):
                        url = loc.text.strip()
                        if url and self._is_same_domain(url, root_domain):
                            link_info = {
                                'url': url,
                                'path': urlparse(url).path,
                                'source': 'sitemap',
                                'priority': 8,  # High priority
                                'relevance_score': self._calculate_relevance(url)
                            }
                            links.append(link_info)
                    
                    # Also check for sitemap index (nested sitemaps)
                    for sitemap in soup.find_all('sitemap'):
                        nested_url = sitemap.find('loc')
                        if nested_url:
                            nested_links = await self._discover_from_sitemap(nested_url.text.strip(), root_domain)
                            links.extend(nested_links)
                    
                    logger.debug("Links found in sitemap", count=len(links), url=sitemap_url)
                    break  # Found sitemap, no need to try others
                    
            except Exception as e:
                logger.debug("Sitemap not found or failed", url=sitemap_url, error=str(e))
                continue
        
        return links
    
    async def _discover_from_robots(self, base_url: str, root_domain: str) -> List[Dict[str, Any]]:
        """Discover links from robots.txt."""
        links: List[Dict[str, Any]] = []
        
        try:
            robots_url = f"{base_url}/robots.txt"
            response = await self.http_client.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Look for Sitemap directive
                for line in content.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        if sitemap_url:
                            sitemap_links = await self._discover_from_sitemap(sitemap_url, root_domain)
                            links.extend(sitemap_links)
                
                logger.debug("Links found from robots.txt", count=len(links))
                
        except Exception as e:
            logger.debug("Robots.txt not found or failed", error=str(e))
        
        return links
    
    async def _discover_from_seo(self, base_url: str, root_domain: str) -> List[Dict[str, Any]]:
        """Discover links from SEO meta tags and structured data."""
        links: List[Dict[str, Any]] = []
        
        try:
            response = await self.http_client.get(base_url)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            
            # Check for JSON-LD structured data
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    import json
                    data = json.loads(script.string)
                    urls = self._extract_urls_from_json(data)
                    for url in urls:
                        if self._is_same_domain(url, root_domain):
                            link_info = {
                                'url': url,
                                'path': urlparse(url).path,
                                'source': 'seo_jsonld',
                                'priority': 6,
                                'relevance_score': self._calculate_relevance(url)
                            }
                            links.append(link_info)
                except Exception:
                    continue
            
            # Check for Open Graph and Twitter Card meta tags
            for meta in soup.find_all('meta', property=re.compile(r'og:|twitter:')):
                content = meta.get('content', '')
                if content and (content.startswith('http://') or content.startswith('https://')):
                    if self._is_same_domain(content, root_domain):
                        link_info = {
                            'url': content,
                            'path': urlparse(content).path,
                            'source': 'seo_meta',
                            'priority': 5,
                            'relevance_score': self._calculate_relevance(content)
                        }
                        links.append(link_info)
            
            logger.debug("Links found from SEO data", count=len(links))
            
        except Exception as e:
            logger.warning("Failed to discover links from SEO", error=str(e))
        
        return links
    
    def _process_link(self, href: str, base_url: str, root_domain: str, element: Any) -> Optional[Dict[str, Any]]:
        """Process a single link and return link info if valid."""
        try:
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Normalize URL
            parsed = urlparse(full_url)
            
            # Filter: must be same domain
            if not self._is_same_domain(full_url, root_domain):
                return None
            
            # Filter: exclude common non-content URLs
            path = parsed.path.lower()
            excluded_patterns = [
                '/wp-admin', '/wp-content', '/wp-includes',
                '/static', '/assets', '/css', '/js', '/images', '/img',
                '/fonts', '/media', '/uploads', '/files',
                '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                '.zip', '.exe', '.dmg', 'mailto:', 'tel:', 'javascript:'
            ]
            
            if any(pattern in path for pattern in excluded_patterns):
                return None
            
            # Get link text for relevance scoring
            link_text = element.get_text(strip=True).lower()
            text_content = link_text
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(full_url, text_content)
            
            # Determine priority based on source and content
            priority = 7  # Default priority for homepage links
            if any(keyword in path.lower() or keyword in text_content for keyword in self.relevant_keywords):
                priority = 9  # High priority for relevant keywords
            
            return {
                'url': full_url,
                'path': parsed.path,
                'source': 'homepage',
                'priority': priority,
                'relevance_score': relevance_score,
                'link_text': link_text[:100]  # Truncate long text
            }
            
        except Exception as e:
            logger.debug("Failed to process link", href=href, error=str(e))
            return None
    
    def _extract_url_from_onclick(self, onclick: str) -> Optional[str]:
        """Extract URL from onclick JavaScript."""
        # Common patterns: window.location.href, window.open, location.href
        patterns = [
            r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]",
            r"window\.open\s*\(['\"]([^'\"]+)['\"]",
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",
            r"location\.replace\s*\(['\"]([^'\"]+)['\"]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_urls_from_json(self, data: Any, urls: Optional[Set[str]] = None) -> Set[str]:
        """Recursively extract URLs from JSON data."""
        if urls is None:
            urls = set()
        
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['url', 'href', 'link', '@id', 'sameAs']:
                    if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                        urls.add(value)
                else:
                    self._extract_urls_from_json(value, urls)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item, urls)
        elif isinstance(data, str) and (data.startswith('http://') or data.startswith('https://')):
            urls.add(data)
        
        return urls
    
    def _is_same_domain(self, url: str, root_domain: str) -> bool:
        """Check if URL belongs to the same domain."""
        try:
            parsed = urlparse(url)
            domain = self.url_processor.extract_root_domain(url)
            return domain.lower() == root_domain.lower()
        except Exception:
            return False
    
    def _calculate_relevance(self, url: str, text: str = "") -> int:
        """Calculate relevance score for a URL (0-10)."""
        score = 5  # Base score
        
        url_lower = url.lower()
        text_lower = text.lower()
        combined = f"{url_lower} {text_lower}"
        
        # Boost score for relevant keywords
        for keyword in self.relevant_keywords:
            if keyword in combined:
                score += 1
        
        # Boost for common contact page patterns
        contact_patterns = ['contact', 'about', 'support', 'help', 'sales']
        for pattern in contact_patterns:
            if pattern in url_lower:
                score += 2
        
        # Cap at 10
        return min(score, 10)
    
    def _deduplicate_and_prioritize(self, links: List[Dict[str, Any]], root_domain: str) -> List[Dict[str, Any]]:
        """Deduplicate links and sort by priority and relevance."""
        # Create a dictionary to deduplicate by URL
        unique_links: Dict[str, Dict[str, Any]] = {}
        
        for link in links:
            url = link.get('url', '')
            if not url:
                continue
            
            # Normalize URL for comparison
            normalized = self.url_processor.normalize_url(url)
            
            # Keep the link with highest priority/relevance
            if normalized not in unique_links:
                unique_links[normalized] = link
            else:
                existing = unique_links[normalized]
                # Update if new link has higher priority or relevance
                if (link.get('priority', 0) > existing.get('priority', 0) or
                    link.get('relevance_score', 0) > existing.get('relevance_score', 0)):
                    unique_links[normalized] = link
        
        # Sort by priority (descending) then relevance (descending)
        sorted_links = sorted(
            unique_links.values(),
            key=lambda x: (x.get('priority', 0), x.get('relevance_score', 0)),
            reverse=True
        )
        
        return sorted_links
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

