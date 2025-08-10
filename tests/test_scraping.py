import pytest
import asyncio
import aiohttp
from httpx import AsyncClient
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from test_api import app, scrape_single_page, scrape_website_async
from bs4 import BeautifulSoup
import json

# Test data
TEST_URLS = [
    "https://httpbin.org/html",
    "https://example.com",
    "https://quotes.toscrape.com"
]

@pytest.fixture
def test_app():
    """Test app fixture"""
    return app

@pytest.fixture
async def async_client():
    """Async client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def aiohttp_session():
    """Aiohttp session fixture"""
    async with aiohttp.ClientSession() as session:
        yield session

class TestScrapingFunctions:
    """Test the core scraping functions"""
    
    @pytest.mark.asyncio
    async def test_scrape_single_page(self, aiohttp_session):
        """Test scraping a single page"""
        url = "https://httpbin.org/html"
        result = await scrape_single_page(aiohttp_session, url)
        
        assert "error" not in result
        assert result["url"] == url
        assert "title" in result
        assert "headings" in result
        assert "paragraphs" in result
        assert "links" in result
        assert "images" in result
        assert "meta" in result
        assert "content_length" in result
        assert result["content_length"] > 0
    
    @pytest.mark.asyncio
    async def test_scrape_single_page_error(self, aiohttp_session):
        """Test scraping a non-existent page"""
        url = "https://httpbin.org/status/404"
        result = await scrape_single_page(aiohttp_session, url)
        
        assert "error" in result
        assert "HTTP 404" in result["error"]
    
    @pytest.mark.asyncio
    async def test_scrape_website_async(self, aiohttp_session):
        """Test scraping a website with multiple pages"""
        url = "https://httpbin.org/html"
        result = await scrape_website_async(url, depth=1, max_pages=2)
        
        assert result["base_url"] == url
        assert result["pages_scraped"] > 0
        assert result["total_time"] > 0
        assert "pages" in result
        assert len(result["pages"]) > 0
        assert "summary" in result
        
        # Check summary data
        summary = result["summary"]
        assert "total_headings" in summary
        assert "total_paragraphs" in summary
        assert "total_links" in summary
        assert "total_images" in summary
        assert "total_content_length" in summary

class TestAPIEndpoints:
    """Test the API endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """Test the root endpoint"""
        response = await async_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert data["message"] == "Web Scraper Test API"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test the health endpoint"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "active_tasks" in data
        assert "total_tasks" in data
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_start_scraping(self, async_client):
        """Test starting a scraping task"""
        payload = {
            "url": "https://httpbin.org/html",
            "depth": 1,
            "max_pages": 2,
            "include_images": False,
            "include_links": True
        }
        
        response = await async_client.post("/scrape", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert "message" in data
        assert data["status"] == "started"
        
        return data["task_id"]
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, async_client):
        """Test getting task status"""
        # First start a task
        payload = {
            "url": "https://httpbin.org/html",
            "depth": 1,
            "max_pages": 1,
            "include_images": False,
            "include_links": True
        }
        
        response = await async_client.post("/scrape", json=payload)
        task_id = response.json()["task_id"]
        
        # Check status
        response = await async_client.get(f"/task/{task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert "progress" in data
        assert "created_at" in data
        assert data["task_id"] == task_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, async_client):
        """Test getting status of non-existent task"""
        response = await async_client.get("/task/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, async_client):
        """Test listing all tasks"""
        response = await async_client.get("/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)
        assert isinstance(data["total"], int)
    
    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(self, async_client):
        """Test the complete scraping workflow"""
        # Start scraping
        payload = {
            "url": "https://httpbin.org/html",
            "depth": 1,
            "max_pages": 1,
            "include_images": False,
            "include_links": True
        }
        
        response = await async_client.post("/scrape", json=payload)
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Wait for completion (with timeout)
        import time
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        while time.time() - start_time < timeout:
            response = await async_client.get(f"/task/{task_id}")
            data = response.json()
            
            if data["status"] == "completed":
                # Get results
                response = await async_client.get(f"/result/{task_id}")
                assert response.status_code == 200
                
                result = response.json()
                assert "base_url" in result
                assert "pages_scraped" in result
                assert "pages" in result
                assert len(result["pages"]) > 0
                
                # Check first page data
                first_page = result["pages"][0]
                assert "url" in first_page
                assert "title" in first_page
                assert "headings" in first_page
                assert "paragraphs" in first_page
                assert "links" in first_page
                assert "images" in first_page
                assert "meta" in result
                assert "content_length" in first_page
                
                return  # Success
            elif data["status"] == "failed":
                pytest.fail(f"Task failed: {data.get('error', 'Unknown error')}")
            
            await asyncio.sleep(1)
        
        pytest.fail("Task did not complete within timeout")

class TestDataExtraction:
    """Test data extraction from HTML"""
    
    def test_beautifulsoup_parsing(self):
        """Test BeautifulSoup HTML parsing"""
        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Main Heading</h1>
                <h2>Sub Heading</h2>
                <p>This is a paragraph with meaningful content.</p>
                <p>Short.</p>
                <a href="https://example.com">Example Link</a>
                <img src="test.jpg" alt="Test Image">
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Test title extraction
        title = soup.find('title')
        assert title.get_text().strip() == "Test Page"
        
        # Test heading extraction
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(tag):
                headings.append(heading.get_text().strip())
        
        assert "Main Heading" in headings
        assert "Sub Heading" in headings
        
        # Test paragraph extraction
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 20:  # Only meaningful paragraphs
                paragraphs.append(text)
        
        assert "This is a paragraph with meaningful content." in paragraphs
        assert "Short." not in paragraphs  # Too short
        
        # Test link extraction
        links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            if href and href.startswith(('http', 'https')):
                links.append({
                    "url": href,
                    "text": a.get_text().strip()[:100]
                })
        
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com"
        assert links[0]["text"] == "Example Link"
        
        # Test image extraction
        images = []
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src:
                images.append({
                    "src": src,
                    "alt": img.get('alt', ''),
                    "title": img.get('title', '')
                })
        
        assert len(images) == 1
        assert images[0]["src"] == "test.jpg"
        assert images[0]["alt"] == "Test Image"

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_invalid_url(self, async_client):
        """Test scraping with invalid URL"""
        payload = {
            "url": "not-a-valid-url",
            "depth": 1,
            "max_pages": 1
        }
        
        response = await async_client.post("/scrape", json=payload)
        # Should handle invalid URL gracefully
        assert response.status_code in [200, 422]  # Either success or validation error
    
    @pytest.mark.asyncio
    async def test_get_result_before_completion(self, async_client):
        """Test getting result before task completion"""
        # Start a task
        payload = {
            "url": "https://httpbin.org/html",
            "depth": 1,
            "max_pages": 1
        }
        
        response = await async_client.post("/scrape", json=payload)
        task_id = response.json()["task_id"]
        
        # Try to get result immediately (should fail)
        response = await async_client.get(f"/result/{task_id}")
        assert response.status_code in [400, 404]  # Should not be available yet

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 