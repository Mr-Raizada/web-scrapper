from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timezone
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
import logging

# Import enhanced scraper
try:
    from enhanced_scraper import EnhancedWebScraper, ScrapingConfig
    ENHANCED_SCRAPER_AVAILABLE = True
except ImportError:
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from enhanced_scraper import EnhancedWebScraper, ScrapingConfig
        ENHANCED_SCRAPER_AVAILABLE = True
    except ImportError:
        # Enhanced scraper not available
        EnhancedWebScraper = None
        ScrapingConfig = None
        ENHANCED_SCRAPER_AVAILABLE = False
        print("Warning: Enhanced scraper module not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Scraper Test API",
    description="Simplified API for testing web scraping functionality without database",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for testing
scraping_results = {}
task_status = {}

class ScrapingRequest(BaseModel):
    url: HttpUrl
    depth: int = 1
    max_pages: int = 10
    include_images: bool = False
    include_links: bool = True

class EnhancedScrapingRequest(BaseModel):
    url: HttpUrl
    timeout: int = 30
    max_retries: int = 2
    delay_between_requests: float = 1.0
    extract_structured_data: bool = True
    extract_media: bool = True
    quality_filter: bool = True

class ScrapingResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

def generate_task_id():
    """Generate a unique task ID"""
    return f"task_{int(time.time())}_{hash(str(time.time()))}"

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
        logger.error(f"Error scraping {url}: {str(e)}")
        return {"error": str(e), "url": url}

async def scrape_website_async(url: str, depth: int = 1, max_pages: int = 10, include_images: bool = False) -> dict:
    """Scrape a website with configurable depth and page limit"""
    start_time = time.time()
    base_url = url
    scraped_pages = []
    visited_urls = set()
    urls_to_visit = [url]
    
    async with aiohttp.ClientSession() as session:
        for current_depth in range(depth):
            if not urls_to_visit or len(scraped_pages) >= max_pages:
                break
                
            current_urls = urls_to_visit.copy()
            urls_to_visit = []
            
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
                        
                        # Collect links for next depth level
                        if current_depth < depth - 1 and include_images:
                            for link in result.get("links", []):
                                link_url = link.get("url")
                                if link_url and link_url.startswith(base_url) and link_url not in visited_urls:
                                    urls_to_visit.append(link_url)
    
    end_time = time.time()
    
    return {
        "base_url": base_url,
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

@app.post("/scrape", response_model=ScrapingResponse)
async def start_scraping(request: ScrapingRequest):
    """Start a scraping task"""
    task_id = generate_task_id()
    
    # Initialize task status
    task_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "request": request.dict()
    }
    
    # Start scraping in background
    asyncio.create_task(run_scraping_task(task_id, request))
    
    return ScrapingResponse(
        task_id=task_id,
        status="started",
        message="Scraping task started successfully"
    )

async def run_scraping_task(task_id: str, request: ScrapingRequest):
    """Run the scraping task in background"""
    try:
        # Update status to processing
        task_status[task_id]["status"] = "processing"
        task_status[task_id]["progress"] = 10
        
        # Perform scraping
        result = await scrape_website_async(
            str(request.url),
            depth=request.depth,
            max_pages=request.max_pages,
            include_images=request.include_images
        )
        
        # Store result
        scraping_results[task_id] = result
        
        # Update task status
        task_status[task_id].update({
            "status": "completed",
            "progress": 100,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Scraping task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scraping task {task_id}: {str(e)}")
        task_status[task_id].update({
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })

@app.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a scraping task"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(**task_status[task_id])

@app.get("/tasks")
async def list_tasks():
    """List all scraping tasks"""
    return {
        "tasks": list(task_status.values()),
        "total": len(task_status)
    }

@app.get("/result/{task_id}")
async def get_scraping_result(task_id: str):
    """Get the result of a completed scraping task"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_status[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    
    if task_id not in scraping_results:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return scraping_results[task_id]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_tasks": len([t for t in task_status.values() if t["status"] == "processing"]),
        "total_tasks": len(task_status)
    }

@app.post("/scrape-enhanced", response_model=ScrapingResponse)
async def start_enhanced_scraping(request: EnhancedScrapingRequest):
    """Start an enhanced scraping task with better data extraction"""
    if not ENHANCED_SCRAPER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced scraper module not available")
    
    task_id = generate_task_id()
    
    # Initialize task status
    task_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": request.dict()
    }
    
    # Start enhanced scraping in background
    asyncio.create_task(run_enhanced_scraping_task(task_id, request))
    
    return ScrapingResponse(
        task_id=task_id,
        status="started",
        message="Enhanced scraping task started successfully"
    )

async def run_enhanced_scraping_task(task_id: str, request: EnhancedScrapingRequest):
    """Run the enhanced scraping task in background"""
    try:
        if not ENHANCED_SCRAPER_AVAILABLE:
            raise Exception("Enhanced scraper module not available")
        # Update status to processing
        task_status[task_id]["status"] = "processing"
        task_status[task_id]["progress"] = 10
        
        # Configure enhanced scraper
        config = ScrapingConfig(
            timeout=request.timeout,
            max_retries=request.max_retries,
            delay_between_requests=request.delay_between_requests
        )
        
        # Perform enhanced scraping
        async with EnhancedWebScraper(config) as scraper:
            result = await scraper.scrape_url(str(request.url))
        
        # Process result
        if "error" in result:
            # Handle error case
            task_status[task_id].update({
                "status": "failed",
                "progress": 0,
                "error": result["error"],
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            # Store successful result
            scraping_results[task_id] = result
            
            # Update task status
            task_status[task_id].update({
                "status": "completed",
                "progress": 100,
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"Enhanced scraping task {task_id} completed")
        
    except Exception as e:
        logger.error(f"Error in enhanced scraping task {task_id}: {str(e)}")
        task_status[task_id].update({
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Web Scraper Test API",
        "version": "2.0.0",  # Updated version
        "endpoints": {
            "POST /scrape": "Start a basic scraping task",
            "POST /scrape-enhanced": "Start an enhanced scraping task with better data extraction",
            "GET /task/{task_id}": "Get task status",
            "GET /result/{task_id}": "Get scraping result",
            "GET /tasks": "List all tasks",
            "GET /health": "Health check"
        },
        "example_requests": {
            "basic": {
                "url": "https://example.com",
                "depth": 1,
                "max_pages": 5,
                "include_images": False,
                "include_links": True
            },
            "enhanced": {
                "url": "https://example.com",
                "timeout": 30,
                "max_retries": 2,
                "delay_between_requests": 1.0,
                "extract_structured_data": True,
                "extract_media": True,
                "quality_filter": True
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 