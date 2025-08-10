from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
celery_app = Celery(
    "web_scraper",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=['src.tasks.scraping_tasks', 'src.tasks.data_processing_tasks']
)

# Celery settings
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
)

# Task routing
celery_app.conf.task_routes = {
    'src.tasks.scraping_tasks.*': {'queue': 'scraping'},
    'src.tasks.data_processing_tasks.*': {'queue': 'processing'},
} 