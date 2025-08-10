#!/usr/bin/env python3
"""
Interactive Web Scraper
Just run this script and enter any website URL to scrape!
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
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
        "scraped_at": datetime.now().isoformat()
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
                "scraped_at": datetime.now().isoformat()
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

def get_user_input():
    """Get user input for scraping parameters"""
    print("🎯 Interactive Web Scraper")
    print("=" * 50)
    
    # Get URL
    while True:
        url = input("🌐 Enter website URL to scrape: ").strip()
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            break
        print("❌ Please enter a valid URL")
    
    # Get depth
    while True:
        try:
            depth_input = input("🔍 Enter scraping depth (1-3, default: 1): ").strip()
            depth = int(depth_input) if depth_input else 1
            if 1 <= depth <= 3:
                break
            print("❌ Depth must be between 1 and 3")
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Get max pages
    while True:
        try:
            pages_input = input("📊 Enter max pages to scrape (1-20, default: 5): ").strip()
            max_pages = int(pages_input) if pages_input else 5
            if 1 <= max_pages <= 20:
                break
            print("❌ Max pages must be between 1 and 20")
        except ValueError:
            print("❌ Please enter a valid number")
    
    return url, depth, max_pages

async def main():
    """Main function"""
    try:
        # Get user input
        url, depth, max_pages = get_user_input()
        
        print(f"\n🚀 Starting to scrape: {url}")
        print(f"📊 Settings: Depth={depth}, Max Pages={max_pages}")
        print("=" * 50)
        
        # Scrape the website
        results = await scrape_website(url, depth, max_pages)
        
        # Print summary
        print_summary(results)
        
        # Ask if user wants to save results
        save_choice = input("\n💾 Save results to file? (y/n, default: y): ").strip().lower()
        if save_choice != 'n':
            save_results(results)
        
        print("\n🎉 Scraping completed successfully!")
        
        # Ask if user wants to scrape another website
        again = input("\n🔄 Scrape another website? (y/n, default: n): ").strip().lower()
        if again == 'y':
            print("\n" + "=" * 50)
            await main()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 