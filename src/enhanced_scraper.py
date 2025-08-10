#!/usr/bin/env python3
"""
Enhanced Web Scraper with improved URL handling and data extraction
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup, Comment
import json
import time
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, List, Optional, Set, Tuple
import logging
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingConfig:
    """Configuration for scraping operations"""
    max_retries: int = 3
    timeout: int = 30
    delay_between_requests: float = 1.0
    user_agent: str = "Enhanced Web Scraper 1.0"
    max_redirects: int = 10
    exclude_patterns: List[str] = None
    
    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                r'\.pdf$', r'\.doc[x]?$', r'\.xls[x]?$', r'\.ppt[x]?$',
                r'\.zip$', r'\.rar$', r'\.tar\.gz$', r'\.exe$', r'\.dmg$',
                r'\.mp[34]$', r'\.avi$', r'\.mov$', r'\.wmv$', r'\.flv$',
                r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.bmp$', r'\.svg$',
                r'mailto:', r'tel:', r'ftp:', r'javascript:'
            ]

class URLProcessor:
    """Handles URL validation, normalization, and filtering"""
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL by removing fragments, sorting params, etc."""
        try:
            parsed = urlparse(url.strip())
            
            # Remove fragment
            parsed = parsed._replace(fragment='')
            
            # Normalize scheme
            if not parsed.scheme:
                parsed = parsed._replace(scheme='https')
            
            # Normalize netloc (domain)
            netloc = parsed.netloc.lower()
            if netloc.startswith('www.') and len(netloc) > 4:
                # Remove www. prefix for consistency
                netloc = netloc[4:]
            parsed = parsed._replace(netloc=netloc)
            
            # Clean path
            path = parsed.path.rstrip('/')
            if not path:
                path = '/'
            parsed = parsed._replace(path=path)
            
            return urlunparse(parsed)
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return url

    @staticmethod
    def is_valid_url(url: str, base_domain: str = None) -> bool:
        """Check if URL is valid and should be scraped"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be http or https
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # If base_domain specified, must be same domain
            if base_domain:
                url_domain = parsed.netloc.lower()
                if url_domain.startswith('www.'):
                    url_domain = url_domain[4:]
                if url_domain != base_domain:
                    return False
            
            return True
        except Exception:
            return False

    @staticmethod
    def should_exclude_url(url: str, exclude_patterns: List[str]) -> bool:
        """Check if URL matches exclusion patterns"""
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

class ContentExtractor:
    """Enhanced content extraction with better data quality"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common navigation/footer text patterns
        skip_patterns = [
            r'^(skip to|jump to|go to)\s+\w+',
            r'^(home|about|contact|privacy|terms)\s*$',
            r'^\s*(©|copyright)\s*\d{4}',
            r'^(follow us|connect with us)',
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return ""
        
        return text

    @staticmethod
    def extract_structured_data(soup: BeautifulSoup) -> Dict:
        """Extract structured data (JSON-LD, microdata, etc.)"""
        structured_data = {}
        
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        json_ld_data = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                json_ld_data.append(data)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        if json_ld_data:
            structured_data['json_ld'] = json_ld_data
        
        # Open Graph
        og_data = {}
        for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            prop = meta.get('property', '')[3:]  # Remove 'og:' prefix
            content = meta.get('content', '')
            if prop and content:
                og_data[prop] = content
        
        if og_data:
            structured_data['open_graph'] = og_data
        
        # Twitter Cards
        twitter_data = {}
        for meta in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            name = meta.get('name', '')[8:]  # Remove 'twitter:' prefix
            content = meta.get('content', '')
            if name and content:
                twitter_data[name] = content
        
        if twitter_data:
            structured_data['twitter'] = twitter_data
        
        return structured_data

    @staticmethod
    def extract_main_content(soup: BeautifulSoup) -> Dict:
        """Extract main content areas with better quality"""
        content = {
            'title': '',
            'headings': [],
            'paragraphs': [],
            'lists': [],
            'tables': [],
            'main_content': ''
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            content['title'] = ContentExtractor.clean_text(title_tag.get_text())
        
        # Alternative title sources
        if not content['title']:
            h1 = soup.find('h1')
            if h1:
                content['title'] = ContentExtractor.clean_text(h1.get_text())
        
        # Remove script, style, and comment elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Extract headings with hierarchy
        headings = []
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(level):
                text = ContentExtractor.clean_text(heading.get_text())
                if text and len(text.split()) >= 2:  # At least 2 words
                    headings.append({
                        'level': int(level[1]),
                        'text': text,
                        'tag': level
                    })
        content['headings'] = headings
        
        # Extract paragraphs with quality filtering
        paragraphs = []
        for p in soup.find_all('p'):
            text = ContentExtractor.clean_text(p.get_text())
            if text and len(text) > 30 and len(text.split()) >= 5:  # Quality filter
                paragraphs.append(text)
        content['paragraphs'] = paragraphs
        
        # Extract lists
        lists = []
        for ul in soup.find_all(['ul', 'ol']):
            list_items = []
            for li in ul.find_all('li'):
                item_text = ContentExtractor.clean_text(li.get_text())
                if item_text:
                    list_items.append(item_text)
            if list_items:
                lists.append({
                    'type': ul.name,
                    'items': list_items
                })
        content['lists'] = lists
        
        # Extract tables
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cell_text = ContentExtractor.clean_text(cell.get_text())
                    cells.append(cell_text)
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({'rows': rows})
        content['tables'] = tables
        
        # Extract main content area
        main_selectors = ['main', 'article', '.content', '.main-content', '#content', '#main']
        main_content = ''
        for selector in main_selectors:
            main_elem = soup.select_one(selector)
            if main_elem:
                main_content = ContentExtractor.clean_text(main_elem.get_text())
                break
        
        if not main_content:
            # Fallback: get all paragraph text
            main_content = ' '.join(content['paragraphs'][:5])  # First 5 paragraphs
        
        content['main_content'] = main_content
        
        return content

    @staticmethod
    def extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract and categorize links"""
        links = []
        seen_urls = set()
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            if not href or href.startswith('#'):
                continue
            
            # Resolve relative URLs
            try:
                full_url = urljoin(base_url, href)
                full_url = URLProcessor.normalize_url(full_url)
            except Exception:
                continue
            
            # Skip duplicates
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            link_text = ContentExtractor.clean_text(a.get_text())
            
            # Categorize link
            parsed = urlparse(full_url)
            base_parsed = urlparse(base_url)
            
            link_type = 'external'
            if parsed.netloc == base_parsed.netloc:
                link_type = 'internal'
            elif not parsed.netloc:
                link_type = 'relative'
            
            links.append({
                'url': full_url,
                'text': link_text,
                'title': a.get('title', ''),
                'type': link_type,
                'rel': a.get('rel', [])
            })
        
        return links

    @staticmethod
    def extract_media(soup: BeautifulSoup, base_url: str) -> Dict:
        """Extract images, videos, and other media"""
        media = {
            'images': [],
            'videos': [],
            'audio': []
        }
        
        # Images
        for img in soup.find_all('img', src=True):
            src = img.get('src', '').strip()
            if not src:
                continue
            
            try:
                full_url = urljoin(base_url, src)
            except Exception:
                continue
            
            media['images'].append({
                'src': full_url,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width'),
                'height': img.get('height'),
                'loading': img.get('loading', 'eager')
            })
        
        # Videos
        for video in soup.find_all('video'):
            video_data = {
                'sources': [],
                'poster': video.get('poster', ''),
                'controls': video.has_attr('controls'),
                'autoplay': video.has_attr('autoplay')
            }
            
            # Video sources
            for source in video.find_all('source', src=True):
                src = source.get('src', '').strip()
                if src:
                    try:
                        full_url = urljoin(base_url, src)
                        video_data['sources'].append({
                            'src': full_url,
                            'type': source.get('type', '')
                        })
                    except Exception:
                        continue
            
            if video_data['sources']:
                media['videos'].append(video_data)
        
        return media

class EnhancedWebScraper:
    """Enhanced web scraper with improved URL handling and data extraction"""
    
    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.session = None
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.config.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def scrape_url(self, url: str, retry_count: int = 0) -> Dict:
        """Scrape a single URL with enhanced error handling"""
        try:
            normalized_url = URLProcessor.normalize_url(url)
            
            # Check if already visited or should be excluded
            if normalized_url in self.visited_urls:
                return {"error": "Already visited", "url": url}
            
            if URLProcessor.should_exclude_url(normalized_url, self.config.exclude_patterns):
                return {"error": "URL excluded by pattern", "url": url}
            
            self.visited_urls.add(normalized_url)
            
            # Make request with retry logic
            async with self.session.get(normalized_url) as response:
                # Handle redirects
                if response.history:
                    final_url = str(response.url)
                    logger.info(f"Redirected from {url} to {final_url}")
                    normalized_url = URLProcessor.normalize_url(final_url)
                
                # Check status
                if response.status != 200:
                    error_msg = f"HTTP {response.status}"
                    if response.status == 404:
                        error_msg = "Page not found"
                    elif response.status == 403:
                        error_msg = "Access forbidden"
                    elif response.status == 500:
                        error_msg = "Server error"
                    
                    return {"error": error_msg, "url": normalized_url, "status_code": response.status}
                
                # Get content
                try:
                    html = await response.text()
                except UnicodeDecodeError:
                    html = await response.text(encoding='utf-8', errors='ignore')
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract all data
                content = ContentExtractor.extract_main_content(soup)
                links = ContentExtractor.extract_links(soup, normalized_url)
                media = ContentExtractor.extract_media(soup, normalized_url)
                structured_data = ContentExtractor.extract_structured_data(soup)
                
                # Enhanced metadata
                meta_data = {}
                for meta in soup.find_all('meta'):
                    name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                    content_attr = meta.get('content')
                    if name and content_attr:
                        meta_data[name.lower()] = content_attr
                
                # Calculate content quality score
                quality_score = self._calculate_quality_score(content, len(html))
                
                # Parse domain info
                parsed_url = urlparse(normalized_url)
                
                result = {
                    "url": normalized_url,
                    "original_url": url,
                    "domain": parsed_url.netloc,
                    "path": parsed_url.path,
                    "title": content['title'],
                    "headings": content['headings'],
                    "paragraphs": content['paragraphs'],
                    "lists": content['lists'],
                    "tables": content['tables'],
                    "main_content": content['main_content'][:1000],  # First 1000 chars
                    "links": links,
                    "media": media,
                    "meta": meta_data,
                    "structured_data": structured_data,
                    "content_length": len(html),
                    "text_length": len(content['main_content']),
                    "quality_score": quality_score,
                    "headings_count": len(content['headings']),
                    "paragraphs_count": len(content['paragraphs']),
                    "links_count": len(links),
                    "images_count": len(media['images']),
                    "videos_count": len(media['videos']),
                    "lists_count": len(content['lists']),
                    "tables_count": len(content['tables']),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "response_time": time.time(),
                    "status_code": response.status,
                    "content_type": response.headers.get('content-type', ''),
                    "last_modified": response.headers.get('last-modified', ''),
                }
                
                return result
                
        except asyncio.TimeoutError:
            if retry_count < self.config.max_retries:
                logger.warning(f"Timeout for {url}, retrying...")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self.scrape_url(url, retry_count + 1)
            return {"error": "Timeout", "url": url}
        
        except aiohttp.ClientError as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Client error for {url}: {e}, retrying...")
                await asyncio.sleep(2 ** retry_count)
                return await self.scrape_url(url, retry_count + 1)
            return {"error": f"Client error: {str(e)}", "url": url}
        
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "url": url}
    
    def _calculate_quality_score(self, content: Dict, html_length: int) -> float:
        """Calculate content quality score (0-1)"""
        score = 0.0
        
        # Title quality
        if content['title'] and len(content['title']) > 10:
            score += 0.2
        
        # Content length
        text_length = len(content['main_content'])
        if text_length > 500:
            score += 0.3
        elif text_length > 200:
            score += 0.2
        elif text_length > 100:
            score += 0.1
        
        # Structure
        if content['headings']:
            score += 0.2
        if content['paragraphs']:
            score += 0.2
        if len(content['paragraphs']) > 3:
            score += 0.1
        
        # Text to HTML ratio (content density)
        if html_length > 0:
            ratio = text_length / html_length
            if ratio > 0.1:
                score += 0.1
            elif ratio > 0.05:
                score += 0.05
        
        return min(1.0, score)
    
    async def scrape_multiple_urls(self, urls: List[str], max_concurrent: int = 5) -> List[Dict]:
        """Scrape multiple URLs concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> Dict:
            async with semaphore:
                result = await self.scrape_url(url)
                # Add delay between requests
                if self.config.delay_between_requests > 0:
                    await asyncio.sleep(self.config.delay_between_requests)
                return result
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "error": f"Exception: {str(result)}",
                    "url": urls[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results

# Usage example and testing functions
async def test_enhanced_scraper():
    """Test the enhanced scraper with various URLs"""
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://quotes.toscrape.com",
        "https://news.ycombinator.com",  # More complex site
    ]
    
    config = ScrapingConfig(
        timeout=30,
        delay_between_requests=1.0,
        max_retries=2
    )
    
    async with EnhancedWebScraper(config) as scraper:
        results = await scraper.scrape_multiple_urls(test_urls, max_concurrent=3)
        
        for result in results:
            if "error" in result:
                print(f"❌ Error scraping {result['url']}: {result['error']}")
            else:
                print(f"✅ Successfully scraped {result['url']}")
                print(f"   Title: {result['title']}")
                print(f"   Quality Score: {result['quality_score']:.2f}")
                print(f"   Content: {len(result['paragraphs'])} paragraphs, {len(result['headings'])} headings")
                print(f"   Links: {result['links_count']} ({len([l for l in result['links'] if l['type'] == 'internal'])} internal)")
                print()

if __name__ == "__main__":
    asyncio.run(test_enhanced_scraper())