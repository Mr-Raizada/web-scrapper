#!/usr/bin/env python3
"""
Quick test script to verify the web scraper API is working
"""

import requests
import json
import time
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running!")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API is not running: {e}")
        return False

def test_scraping():
    """Test the scraping functionality"""
    print("\n🧪 Testing scraping functionality...")
    
    # Test data
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://quotes.toscrape.com"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📋 Test {i}: Scraping {url}")
        print("-" * 40)
        
        try:
            # Start scraping
            payload = {
                "url": url,
                "depth": 1,
                "max_pages": 2,
                "include_images": False,
                "include_links": True
            }
            
            print("🚀 Starting scraping task...")
            response = requests.post("http://localhost:8000/scrape", json=payload, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Failed to start scraping: {response.status_code}")
                print(f"Response: {response.text}")
                continue
            
            data = response.json()
            task_id = data["task_id"]
            print(f"✅ Task started: {task_id}")
            
            # Wait for completion
            print("⏳ Waiting for completion...")
            start_time = time.time()
            timeout = 30
            
            while time.time() - start_time < timeout:
                # Check status
                status_response = requests.get(f"http://localhost:8000/task/{task_id}", timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data["status"] == "completed":
                        # Get results
                        result_response = requests.get(f"http://localhost:8000/result/{task_id}", timeout=5)
                        if result_response.status_code == 200:
                            result = result_response.json()
                            
                            print("✅ Scraping completed!")
                            print(f"📊 Pages scraped: {result['pages_scraped']}")
                            print(f"⏱️  Total time: {result['total_time']}s")
                            
                            if result['pages']:
                                first_page = result['pages'][0]
                                print(f"📄 First page title: {first_page.get('title', 'No title')}")
                                print(f"📝 Headings found: {len(first_page.get('headings', []))}")
                                print(f"📖 Paragraphs found: {len(first_page.get('paragraphs', []))}")
                                print(f"🔗 Links found: {len(first_page.get('links', []))}")
                            
                            break
                        else:
                            print(f"❌ Failed to get results: {result_response.status_code}")
                            break
                    elif status_data["status"] == "failed":
                        print(f"❌ Task failed: {status_data.get('error', 'Unknown error')}")
                        break
                    else:
                        print(f"⏳ Status: {status_data['status']} ({status_data['progress']}%)")
                        time.sleep(2)
                else:
                    print(f"❌ Failed to check status: {status_response.status_code}")
                    break
            else:
                print("❌ Task timed out")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")

def test_api_endpoints():
    """Test all API endpoints"""
    print("\n🔧 Testing API endpoints...")
    
    endpoints = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/tasks", "List tasks"),
    ]
    
    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            else:
                response = requests.post(f"http://localhost:8000{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
            else:
                print(f"❌ {description}: {response.status_code}")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")

def main():
    """Main function"""
    print("🎯 Web Scraper API Quick Test")
    print("=" * 40)
    
    # Test if API is running
    if not test_api_health():
        print("\n🚀 Starting API...")
        print("Please run: python test_scraper.py")
        print("Then run this test again.")
        return
    
    # Test API endpoints
    test_api_endpoints()
    
    # Test scraping
    test_scraping()
    
    print("\n" + "=" * 40)
    print("🎉 Test completed!")
    print("📖 API Documentation: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 