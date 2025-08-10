from celery import current_task
from src.celery_app import celery_app
import motor.motor_asyncio
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import sys
import os

# Add scraper directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../scraper'))

load_dotenv()

@celery_app.task(bind=True)
def scrape_website(self, url: str, task_id: str, user_id: str):
    """
    Celery task to scrape a website
    """
    try:
        # Update task status to running
        asyncio.run(update_task_status(task_id, "running"))
        
        # Get Scrapy settings
        settings = get_project_settings()
        settings.set('FEEDS', {
            'items.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
            }
        })
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Import and run spider
        from scraper.scraper.spiders.base_spider import WebScraperSpider
        process.crawl(WebScraperSpider, url=url, task_id=task_id)
        process.start()
        
        # Update task status to completed
        asyncio.run(update_task_status(task_id, "completed"))
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'url': url,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # Update task status to failed
        asyncio.run(update_task_status(task_id, "failed", error=str(e)))
        
        return {
            'task_id': task_id,
            'status': 'failed',
            'url': url,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True)
def scrape_multiple_websites(self, urls: list, task_id: str, user_id: str):
    """
    Celery task to scrape multiple websites
    """
    results = []
    
    for i, url in enumerate(urls):
        try:
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': i + 1, 'total': len(urls), 'url': url}
            )
            
            # Scrape individual URL
            result = scrape_website.delay(url, f"{task_id}_{i}", user_id)
            results.append(result.get())
            
        except Exception as e:
            results.append({
                'url': url,
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'task_id': task_id,
        'status': 'completed',
        'results': results,
        'total_urls': len(urls),
        'timestamp': datetime.utcnow().isoformat()
    }

async def update_task_status(task_id: str, status: str, error: str = None):
    """
    Update task status in MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        if status == 'completed':
            update_data['completed_at'] = datetime.utcnow()
        elif status == 'failed' and error:
            update_data['error'] = error
            update_data['completed_at'] = datetime.utcnow()
        
        await db.tasks.update_one(
            {'_id': task_id},
            {'$set': update_data}
        )
        
    except Exception as e:
        print(f"Error updating task status: {e}") 