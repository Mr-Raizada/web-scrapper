#!/usr/bin/env python3
"""
Simple test script to run the web scraper test API
"""

import uvicorn
import asyncio
import aiohttp
import json
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from test_api import app

async def test_scraping():
    """Test the scraping functionality"""
    print("🚀 Starting Web Scraper Test API...")
    print("=" * 50)
    
    # Test URLs
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://quotes.toscrape.com"
    ]
    
    print("📋 Available test URLs:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    print("\n🔧 API Endpoints:")
    print("  POST /scrape - Start scraping")
    print("  GET /task/{task_id} - Check task status")
    print("  GET /result/{task_id} - Get results")
    print("  GET /tasks - List all tasks")
    print("  GET /health - Health check")
    
    print("\n🌐 API will be available at: http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("=" * 50)

def main():
    """Main function to run the test API"""
    print("🎯 Web Scraper Test API")
    print("This API runs without database for testing scraping functionality")
    print()
    
    # Run the async test
    asyncio.run(test_scraping())
    
    # Start the server
    print("\n🚀 Starting server...")
    uvicorn.run(
        "test_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 