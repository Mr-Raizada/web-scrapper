#!/usr/bin/env python3
"""
Simple command-line web scraper
Usage: python simple_scraper.py <url>
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import sys
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

async def scrape_website(url: str, depth: int = 1, max_pages: int = 5):
    """Scrape a website and extract data"""
    print(f"🕷️  Starting to scrape: {url}")
    print(f"📊 Depth: {depth}, Max pages: {max_pages}")
    print("=" * 50)
    
    start_time = time.time()
    scraped_pages = []
    visited_urls = set()
    urls_to_visit = [url]
    
    async with aiohttp.ClientSession() as session:
        for current_depth in range(depth):
            if not urls_to_visit or len(scraped_pages) >= max_pages:
                break
                
            current_urls = urls_to_visit.copy()
            urls_to_visit = []
            
            print(f"🔍 Scraping depth {current_depth + 1}...")
            
            # Scrape current level URLs
            tasks = []
            for url_to_scrape in current_urls:
                if url_to_scrape not in visited_urls and len(scraped_pages) < max_pages:
                    visited_urls.add(url_to_scrape)
                    tasks.append(scrape_single_page(session, url_to_scrape))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, dict) and "error" not in result:
                        scraped_pages.append(result)
                        print(f"✅ Scraped: {result['url']}")
                        print(f"   📄 Title: {result['title']}")
                        print(f"   📝 Headings: {len(result['headings'])}")
                        print(f"   📖 Paragraphs: {len(result['paragraphs'])}")
                        print(f"   🔗 Links: {len(result['links'])}")
                        print(f"   🖼️  Images: {len(result['images'])}")
                        print()
                        
                        # Collect links for next depth level
                        if current_depth < depth - 1:
                            for link in result.get("links", []):
                                link_url = link.get("url")
                                if link_url and link_url.startswith(url) and link_url not in visited_urls:
                                    urls_to_visit.append(link_url)
                    elif isinstance(result, Exception):
                        print(f"❌ Error: {result}")
    
    end_time = time.time()
    
    # Create summary
    summary = {
        "base_url": url,
        "pages_scraped": len(scraped_pages),
        "total_time": round(end_time - start_time, 2),
        "depth": depth,
        "max_pages": max_pages,
        "pages": scraped_pages,
        "summary": {
            "total_headings": sum(len(page.get("headings", [])) for page in scraped_pages),
            "total_paragraphs": sum(len(page.get("paragraphs", [])) for page in scraped_pages),
            "total_links": sum(len(page.get("links", [])) for page in scraped_pages),
            "total_images": sum(len(page.get("images", [])) for page in scraped_pages),
            "total_content_length": sum(page.get("content_length", 0) for page in scraped_pages)
        },
        "scraped_at": datetime.utcnow().isoformat()
    }
    
    return summary

async def scrape_single_page(session: aiohttp.ClientSession, url: str) -> dict:
    """Scrape a single page and extract data"""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status != 200:
                return {"error": f"HTTP {response.status}", "url": url}
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract basic data
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"
            
            # Extract headings
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for heading in soup.find_all(tag):
                    headings.append(heading.get_text().strip())
            
            # Extract paragraphs
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if text and len(text) > 20:  # Only meaningful paragraphs
                    paragraphs.append(text)
            
            # Extract links
            links = []
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if href and href.startswith(('http', 'https')):
                    links.append({
                        "url": href,
                        "text": a.get_text().strip()[:100]
                    })
            
            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img.get('src')
                if src:
                    full_url = urljoin(url, src)
                    images.append({
                        "src": full_url,
                        "alt": img.get('alt', ''),
                        "title": img.get('title', '')
                    })
            
            # Extract meta data
            meta_data = {}
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    meta_data[name] = content
            
            return {
                "url": url,
                "title": title_text,
                "headings": headings[:20],  # Limit to 20 headings
                "paragraphs": paragraphs[:50],  # Limit to 50 paragraphs
                "links": links[:100],  # Limit to 100 links
                "images": images[:50],  # Limit to 50 images
                "meta": meta_data,
                "content_length": len(html),
                "headings_count": len(headings),
                "paragraphs_count": len(paragraphs),
                "links_count": len(links),
                "images_count": len(images),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {"error": str(e), "url": url}

def save_results(results: dict, filename: str = None):
    """Save results to JSON file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraped_data_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Results saved to: {filename}")

def print_summary(results: dict):
    """Print a summary of the scraping results"""
    print("\n" + "=" * 50)
    print("📊 SCRAPING SUMMARY")
    print("=" * 50)
    print(f"🌐 Base URL: {results['base_url']}")
    print(f"📄 Pages Scraped: {results['pages_scraped']}")
    print(f"⏱️  Total Time: {results['total_time']}s")
    print(f"🔍 Depth: {results['depth']}")
    print(f"📊 Max Pages: {results['max_pages']}")
    
    summary = results['summary']
    print(f"\n📈 CONTENT SUMMARY:")
    print(f"   📝 Total Headings: {summary['total_headings']}")
    print(f"   📖 Total Paragraphs: {summary['total_paragraphs']}")
    print(f"   🔗 Total Links: {summary['total_links']}")
    print(f"   🖼️  Total Images: {summary['total_images']}")
    print(f"   📏 Total Content Length: {summary['total_content_length']:,} characters")
    
    if results['pages']:
        print(f"\n📄 FIRST PAGE DETAILS:")
        first_page = results['pages'][0]
        print(f"   📄 Title: {first_page['title']}")
        print(f"   📝 Headings: {len(first_page['headings'])}")
        print(f"   📖 Paragraphs: {len(first_page['paragraphs'])}")
        print(f"   🔗 Links: {len(first_page['links'])}")
        print(f"   🖼️  Images: {len(first_page['images'])}")

async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python simple_scraper.py <url> [depth] [max_pages]")
        print("Example: python simple_scraper.py https://example.com 1 5")
        print("\nAvailable test URLs:")
        print("  https://httpbin.org/html")
        print("  https://example.com")
        print("  https://quotes.toscrape.com")
        return
    
    url = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    print("🎯 Simple Web Scraper")
    print("=" * 50)
    
    try:
        # Scrape the website
        results = await scrape_website(url, depth, max_pages)
        
        # Print summary
        print_summary(results)
        
        # Save results
        save_results(results)
        
        print("\n🎉 Scraping completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 