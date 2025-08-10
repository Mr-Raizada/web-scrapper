from celery import current_task
from src.celery_app import celery_app
import motor.motor_asyncio
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
import json
from typing import List, Dict, Any

load_dotenv()

@celery_app.task(bind=True)
def process_scraped_data(self, task_id: str, data_id: str):
    """
    Process and clean scraped data
    """
    try:
        # Update processing status
        asyncio.run(update_processing_status(data_id, "processing"))
        
        # Get scraped data from MongoDB
        data = asyncio.run(get_scraped_data(data_id))
        
        if not data:
            raise Exception("Data not found")
        
        # Process the data
        processed_data = process_data(data)
        
        # Save processed data
        asyncio.run(save_processed_data(data_id, processed_data))
        
        # Update status to completed
        asyncio.run(update_processing_status(data_id, "completed"))
        
        return {
            'data_id': data_id,
            'status': 'completed',
            'processed_items': len(processed_data),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # Update status to failed
        asyncio.run(update_processing_status(data_id, "failed", error=str(e)))
        
        return {
            'data_id': data_id,
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True)
def export_data_task(self, data_ids: List[str], format: str, user_id: str):
    """
    Export data in specified format
    """
    try:
        # Get data from MongoDB
        all_data = []
        for data_id in data_ids:
            data = asyncio.run(get_processed_data(data_id))
            if data:
                all_data.extend(data)
        
        # Export based on format
        if format == 'csv':
            result = export_to_csv(all_data)
        elif format == 'excel':
            result = export_to_excel(all_data)
        elif format == 'json':
            result = export_to_json(all_data)
        else:
            raise Exception(f"Unsupported format: {format}")
        
        # Save export record
        export_id = asyncio.run(save_export_record(user_id, format, len(all_data)))
        
        return {
            'export_id': export_id,
            'format': format,
            'records_exported': len(all_data),
            'file_path': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

def process_data(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process and clean raw scraped data
    """
    processed_items = []
    
    try:
        # Extract and clean title
        title = clean_text(raw_data.get('title', ''))
        
        # Extract and clean headings
        headings = [clean_text(h) for h in raw_data.get('headings', [])]
        headings = [h for h in headings if h and len(h) > 3]
        
        # Extract and clean paragraphs
        paragraphs = [clean_text(p) for p in raw_data.get('paragraphs', [])]
        paragraphs = [p for p in paragraphs if p and len(p) > 20]
        
        # Create processed item
        processed_item = {
            'url': raw_data.get('url', ''),
            'title': title,
            'headings': headings[:10],  # Limit to first 10 headings
            'paragraphs': paragraphs[:20],  # Limit to first 20 paragraphs
            'meta': raw_data.get('meta', {}),
            'processed_at': datetime.utcnow().isoformat(),
            'content_length': len(raw_data.get('content', '')),
            'headings_count': len(headings),
            'paragraphs_count': len(paragraphs)
        }
        
        processed_items.append(processed_item)
        
    except Exception as e:
        print(f"Error processing data: {e}")
    
    return processed_items

def clean_text(text: str) -> str:
    """
    Clean and normalize text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove special characters (keep alphanumeric, spaces, and basic punctuation)
    import re
    text = re.sub(r'[^\w\s\.\,\!\?\-\:]', '', text)
    
    return text.strip()

def export_to_csv(data: List[Dict[str, Any]]) -> str:
    """
    Export data to CSV format
    """
    df = pd.DataFrame(data)
    filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = f"exports/{filename}"
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    
    df.to_csv(filepath, index=False)
    return filepath

def export_to_excel(data: List[Dict[str, Any]]) -> str:
    """
    Export data to Excel format
    """
    df = pd.DataFrame(data)
    filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"exports/{filename}"
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    
    df.to_excel(filepath, index=False)
    return filepath

def export_to_json(data: List[Dict[str, Any]]) -> str:
    """
    Export data to JSON format
    """
    filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = f"exports/{filename}"
    
    # Ensure exports directory exists
    os.makedirs("exports", exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filepath

async def get_scraped_data(data_id: str) -> Dict[str, Any]:
    """
    Get scraped data from MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        data = await db.scraped_data.find_one({'_id': data_id})
        return data
        
    except Exception as e:
        print(f"Error getting scraped data: {e}")
        return None

async def get_processed_data(data_id: str) -> List[Dict[str, Any]]:
    """
    Get processed data from MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        data = await db.processed_data.find_one({'_id': data_id})
        return data.get('data', []) if data else []
        
    except Exception as e:
        print(f"Error getting processed data: {e}")
        return []

async def save_processed_data(data_id: str, processed_data: List[Dict[str, Any]]):
    """
    Save processed data to MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        await db.processed_data.insert_one({
            '_id': data_id,
            'data': processed_data,
            'created_at': datetime.utcnow(),
            'status': 'completed'
        })
        
    except Exception as e:
        print(f"Error saving processed data: {e}")

async def update_processing_status(data_id: str, status: str, error: str = None):
    """
    Update processing status in MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        update_data = {
            'processing_status': status,
            'updated_at': datetime.utcnow()
        }
        
        if error:
            update_data['error'] = error
        
        await db.scraped_data.update_one(
            {'_id': data_id},
            {'$set': update_data}
        )
        
    except Exception as e:
        print(f"Error updating processing status: {e}")

async def save_export_record(user_id: str, format: str, record_count: int) -> str:
    """
    Save export record to MongoDB
    """
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client.scraper_db
        
        import uuid
        export_id = str(uuid.uuid4())
        
        await db.exports.insert_one({
            '_id': export_id,
            'user_id': user_id,
            'format': format,
            'record_count': record_count,
            'created_at': datetime.utcnow(),
            'status': 'completed'
        })
        
        return export_id
        
    except Exception as e:
        print(f"Error saving export record: {e}")
        return None 