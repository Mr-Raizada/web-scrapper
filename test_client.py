#!/usr/bin/env python3
"""
Test client for the Web Scraper Test API
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

class ScraperTestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def start_scraping(self, url: str, depth: int = 1, max_pages: int = 5) -> Dict[str, Any]:
        """Start a scraping task"""
        payload = {
            "url": url,
            "depth": depth,
            "max_pages": max_pages,
            "include_images": False,
            "include_links": True
        }
        
        async with self.session.post(f"{self.base_url}/scrape", json=payload) as response:
            return await response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        async with self.session.get(f"{self.base_url}/task/{task_id}") as response:
            return await response.json()
    
    async def get_result(self, task_id: str) -> Dict[str, Any]:
        """Get scraping result"""
        async with self.session.get(f"{self.base_url}/result/{task_id}") as response:
            return await response.json()
    
    async def wait_for_completion(self, task_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for task completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.get_task_status(task_id)
            
            if status["status"] == "completed":
                return await self.get_result(task_id)
            elif status["status"] == "failed":
                raise Exception(f"Task failed: {status.get('error', 'Unknown error')}")
            
            print(f"⏳ Task {task_id}: {status['status']} ({status['progress']}%)")
            await asyncio.sleep(2)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")

async def test_scraping_workflow():
    """Test the complete scraping workflow"""
    print("🧪 Testing Web Scraper API")
    print("=" * 40)
    
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://quotes.toscrape.com"
    ]
    
    async with ScraperTestClient() as client:
        for i, url in enumerate(test_urls, 1):
            print(f"\n📋 Test {i}: Scraping {url}")
            print("-" * 30)
            
            try:
                # Start scraping
                print("🚀 Starting scraping task...")
                response = await client.start_scraping(url, depth=1, max_pages=3)
                task_id = response["task_id"]
                print(f"✅ Task started: {task_id}")
                
                # Wait for completion
                print("⏳ Waiting for completion...")
                result = await client.wait_for_completion(task_id, timeout=30)
                
                # Display results
                print("✅ Scraping completed!")
                print(f"📊 Pages scraped: {result['pages_scraped']}")
                print(f"⏱️  Total time: {result['total_time']}s")
                
                if result['pages']:
                    first_page = result['pages'][0]
                    print(f"📄 First page title: {first_page.get('title', 'No title')}")
                    print(f"📝 Headings found: {len(first_page.get('headings', []))}")
                    print(f"📖 Paragraphs found: {len(first_page.get('paragraphs', []))}")
                    print(f"🔗 Links found: {len(first_page.get('links', []))}")
                
                print("=" * 40)
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                print("=" * 40)

async def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    
    async with ScraperTestClient() as client:
        async with client.session.get(f"{client.base_url}/health") as response:
            health = await response.json()
            print(f"✅ Health check: {health['status']}")
            print(f"📊 Active tasks: {health['active_tasks']}")
            print(f"📈 Total tasks: {health['total_tasks']}")

def main():
    """Main function"""
    print("🎯 Web Scraper Test Client")
    print("This client tests the scraping API functionality")
    print()
    
    async def run_tests():
        await test_health_check()
        await test_scraping_workflow()
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main() 