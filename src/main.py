from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import motor.motor_asyncio
import redis.asyncio as redis
import jwt
import bcrypt
from datetime import datetime, timedelta
import uuid
import os
import gzip
import json
from dotenv import load_dotenv

# Import custom error handling and logging
from core.exceptions import (
    AppException, ValidationException, AuthenticationException,
    AuthorizationException, NotFoundException, RateLimitException,
    ScrapingException, DatabaseException, ExternalServiceException,
    app_exception_handler, validation_exception_handler, python_exception_handler
)
from core.logging_config import logger, LoggingMiddleware

# Import ML service
from services.ml_service import MLService

load_dotenv()

app = FastAPI(
    title="Web Scraper API",
    description="Enterprise-level web scraping system with advanced features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add performance optimization middlewares
app.add_middleware(LoggingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, python_exception_handler)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_db()

# Security
security = HTTPBearer(auto_error=False)  # Don't auto-error for missing auth in dev mode

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = None
db = None

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

# Initialize database connections
async def init_db():
    global client, db, redis_client
    try:
        if DEV_MODE:
            # In dev mode, create in-memory storage if MongoDB/Redis not available
            logger.warning("Running in development mode with in-memory storage")
            return
        
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        db = client.scraper_db
        redis_client = redis.from_url(REDIS_URL)
        
        # Test connections
        await client.admin.command('ping')
        await redis_client.ping()
        logger.info("Database connections established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if DEV_MODE:
            logger.warning("Continuing in development mode with limited functionality")
        else:
            raise e

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Development mode
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"

# In-memory storage for development
if DEV_MODE:
    dev_users = {}
    dev_tasks = {}
    dev_data = {}

# Initialize ML service
ml_service = MLService()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    id: str
    username: str
    email: str

class TaskCreate(BaseModel):
    url: HttpUrl

class Task(BaseModel):
    id: str
    url: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None

class DataSubmit(BaseModel):
    url: HttpUrl
    title: str
    headings: List[str]
    paragraphs: List[str]

class ScrapeRequest(BaseModel):
    url: str
    depth: int = 1
    max_pages: int = 5

class EnhancedScrapeRequest(BaseModel):
    url: str
    depth: int = 1
    max_pages: int = 5
    include_ml_analysis: bool = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Authentication functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if DEV_MODE:
        # In development mode, return a mock user without authentication
        return User(id="dev-user-id", username="devuser", email="dev@example.com")
    
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if DEV_MODE:
        # Use in-memory storage for development
        user = dev_users.get(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(id=user["_id"], username=user["username"], email=user["email"])
    else:
        user = await db.users.find_one({"_id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(id=user["_id"], username=user["username"], email=user["email"])

# Auth endpoints
@app.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    if DEV_MODE:
        # Use in-memory storage for development
        # Check if user already exists
        for user in dev_users.values():
            if user["email"] == user_data.email:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_id = str(uuid.uuid4())
        user_doc = {
            "_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password.decode('utf-8'),
            "created_at": datetime.utcnow()
        }
        
        dev_users[user_id] = user_doc
        
        # Create access token
        access_token = create_access_token(data={"sub": user_id})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(id=user_id, username=user_data.username, email=user_data.email)
        )
    else:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_id = str(uuid.uuid4())
        user_doc = {
            "_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password.decode('utf-8'),
            "created_at": datetime.utcnow()
        }
        
        await db.users.insert_one(user_doc)
        
        # Create access token
        access_token = create_access_token(data={"sub": user_id})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(id=user_id, username=user_data.username, email=user_data.email)
        )

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    if DEV_MODE:
        # Use in-memory storage for development
        # Find user
        user = None
        for u in dev_users.values():
            if u["email"] == user_data.email:
                user = u
                break
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not bcrypt.checkpw(user_data.password.encode('utf-8'), user["password"].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create access token
        access_token = create_access_token(data={"sub": user["_id"]})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(id=user["_id"], username=user["username"], email=user["email"])
        )
    else:
        # Find user
        user = await db.users.find_one({"email": user_data.email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not bcrypt.checkpw(user_data.password.encode('utf-8'), user["password"].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create access token
        access_token = create_access_token(data={"sub": user["_id"]})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(id=user["_id"], username=user["username"], email=user["email"])
        )

# Task endpoints
@app.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    task_doc = {
        "_id": task_id,
        "url": str(task_data.url),
        "status": "pending",
        "user_id": current_user.id,
        "created_at": datetime.utcnow()
    }
    
    if DEV_MODE:
        # Use in-memory storage for development
        dev_tasks[task_id] = task_doc
        
        # Simulate task completion for development
        import asyncio
        await asyncio.sleep(2)  # Simulate processing time
        
        # Update task status to completed with mock data
        dev_tasks[task_id]["status"] = "completed"
        dev_tasks[task_id]["completed_at"] = datetime.utcnow()
        dev_tasks[task_id]["result"] = {
            "title": f"Mock title for {task_data.url}",
            "headings": ["Mock Heading 1", "Mock Heading 2", "Mock Heading 3"],
            "paragraphs": ["Mock paragraph 1", "Mock paragraph 2", "Mock paragraph 3"]
        }
        
        return Task(
            id=task_id,
            url=str(task_data.url),
            status="completed",
            created_at=task_doc["created_at"],
            completed_at=dev_tasks[task_id]["completed_at"],
            result=dev_tasks[task_id]["result"]
        )
    else:
        await db.tasks.insert_one(task_doc)
        
        # Cache the task
        await redis_client.setex(f"task:{task_id}", 3600, str(task_doc))
        
        # Start Celery task
        from src.tasks.scraping_tasks import scrape_website
        scrape_website.delay(str(task_data.url), task_id, current_user.id)
        
        return Task(
            id=task_id,
            url=str(task_data.url),
            status="pending",
            created_at=task_doc["created_at"]
        )

@app.get("/tasks", response_model=List[Task])
async def get_tasks(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    compression: bool = Query(True, description="Enable response compression")
):
    """Get paginated tasks with optional filtering and compression"""
    if DEV_MODE:
        # Use in-memory storage for development
        user_tasks = [task for task in dev_tasks.values() if task["user_id"] == current_user.id]
        
        # Apply status filter
        if status:
            user_tasks = [task for task in user_tasks if task["status"] == status]
        
        # Sort by created_at (newest first)
        user_tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        skip = (page - 1) * page_size
        tasks = user_tasks[skip:skip + page_size]
        
        # Convert to Task objects
        task_objects = []
        for task in tasks:
            task_objects.append(Task(
                id=task["_id"],
                url=task["url"],
                status=task["status"],
                created_at=task["created_at"],
                completed_at=task.get("completed_at"),
                result=task.get("result"),
                error=task.get("error")
            ))
        
        return task_objects
    else:
        # Try to get from cache first
        cache_key = f"tasks:{current_user.id}:{page}:{page_size}:{status}"
        cached_tasks = await redis_client.get(cache_key)
        
        if cached_tasks:
            return json.loads(cached_tasks)
        
        # Build query
        query = {"user_id": current_user.id}
        if status:
            query["status"] = status
        
        # Get from database with pagination
        skip = (page - 1) * page_size
        cursor = db.tasks.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        
        tasks = []
        async for task in cursor:
            tasks.append(Task(
                id=task["_id"],
                url=task["url"],
                status=task["status"],
                created_at=task["created_at"],
                completed_at=task.get("completed_at"),
                result=task.get("result"),
                error=task.get("error")
            ))
        
        # Cache the results
        await redis_client.setex(cache_key, 300, json.dumps(tasks, default=str))
        
        # Apply compression for large responses
        if compression and len(tasks) > 10:
            json_str = json.dumps(tasks, default=str)
            compressed_data = gzip.compress(json_str.encode('utf-8'))
            
            return StreamingResponse(
                iter([compressed_data]),
                media_type="application/json",
                headers={"Content-Encoding": "gzip"}
            )
        
        return tasks

# Data submission endpoint
@app.post("/data")
async def submit_data(data: DataSubmit, current_user: User = Depends(get_current_user)):
    data_id = str(uuid.uuid4())
    data_doc = {
        "_id": data_id,
        "url": str(data.url),
        "title": data.title,
        "headings": data.headings,
        "paragraphs": data.paragraphs,
        "user_id": current_user.id,
        "created_at": datetime.utcnow()
    }
    
    await db.scraped_data.insert_one(data_doc)
    
    # Cache the data
    await redis_client.setex(f"data:{data_id}", 3600, str(data_doc))
    
    # Start data processing task
    from src.tasks.data_processing_tasks import process_scraped_data
    process_scraped_data.delay(data_id, data_id)
    
    return {"message": "Data submitted successfully", "id": data_id}

# Include monitoring router
from routers import monitoring

app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])

# Data processing endpoints
@app.post("/process/{data_id}")
async def process_data_endpoint(data_id: str, current_user: User = Depends(get_current_user)):
    from src.tasks.data_processing_tasks import process_scraped_data
    task = process_scraped_data.delay(data_id, data_id)
    return {"message": "Data processing started", "task_id": task.id}

@app.post("/export")
async def export_data_endpoint(
    data_ids: List[str],
    format: str,
    current_user: User = Depends(get_current_user)
):
    from src.tasks.data_processing_tasks import export_data_task
    task = export_data_task.delay(data_ids, format, current_user.id)
    return {"message": "Export started", "task_id": task.id}

@app.get("/task/{task_id}")
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get task details by ID"""
    if DEV_MODE:
        task = dev_tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    else:
        # Production implementation would query database
        task = await db.tasks.find_one({"_id": task_id, "user_id": current_user.id})
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

@app.get("/result/{task_id}")
async def get_task_result(task_id: str, current_user: User = Depends(get_current_user)):
    """Get task result by ID"""
    if DEV_MODE:
        task = dev_tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")
        
        return task.get("result", {})
    else:
        # Production implementation would query database
        task = await db.tasks.find_one({"_id": task_id, "user_id": current_user.id})
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")
        
        return task.get("result", {})

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    from src.celery_app import celery_app
    task_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

@app.get("/processed-data")
async def get_processed_data(current_user: User = Depends(get_current_user)):
    cursor = db.processed_data.find({"user_id": current_user.id}).sort("created_at", -1)
    processed_data = []
    async for data in cursor:
        processed_data.append({
            "id": data["_id"],
            "url": data.get("url", ""),
            "title": data.get("title", ""),
            "headings": data.get("headings", []),
            "paragraphs": data.get("paragraphs", []),
            "meta": data.get("meta", {}),
            "processed_at": data.get("processed_at", ""),
            "content_length": data.get("content_length", 0),
            "headings_count": data.get("headings_count", 0),
            "paragraphs_count": data.get("paragraphs_count", 0)
        })
    return processed_data

@app.get("/processing-tasks")
async def get_processing_tasks(current_user: User = Depends(get_current_user)):
    cursor = db.tasks.find({"user_id": current_user.id, "type": "processing"}).sort("created_at", -1)
    tasks = []
    async for task in cursor:
        tasks.append({
            "id": task["_id"],
            "status": task["status"],
            "data_id": task.get("data_id", ""),
            "created_at": task["created_at"].isoformat(),
            "result": task.get("result"),
            "error": task.get("error")
        })
    return tasks

@app.get("/export-tasks")
async def get_export_tasks(current_user: User = Depends(get_current_user)):
    cursor = db.exports.find({"user_id": current_user.id}).sort("created_at", -1)
    tasks = []
    async for task in cursor:
        tasks.append({
            "id": task["_id"],
            "format": task["format"],
            "status": task["status"],
            "record_count": task["record_count"],
            "file_path": task.get("file_path"),
            "created_at": task["created_at"].isoformat(),
            "error": task.get("error")
        })
    return tasks

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Basic scraping endpoint
@app.post("/scrape")
async def scrape_basic(
    request: ScrapeRequest,
    current_user: User = Depends(get_current_user)
):
    """Basic scraping endpoint"""
    try:
        # Create task
        task_id = str(uuid.uuid4())
        task_doc = {
            "_id": task_id,
            "url": request.url,
            "status": "processing",
            "user_id": current_user.id,
            "created_at": datetime.utcnow(),
            "enhanced": False
        }
        
        if DEV_MODE:
            dev_tasks[task_id] = task_doc
            
            # Use actual scraping instead of mock data
            try:
                import urllib.request
                import urllib.error
                from bs4 import BeautifulSoup
                
                # Scrape the actual URL using urllib
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                req = urllib.request.Request(request.url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    html_content = response.read().decode('utf-8', errors='ignore')
                    
                    # Parse HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    title = title_tag.get_text().strip() if title_tag else "No title found"
                    
                    # Extract headings
                    headings = []
                    for h_tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        text = h_tag.get_text().strip()
                        if text and len(text) > 2:
                            headings.append(text)
                    
                    # Extract paragraphs
                    paragraphs = []
                    for p_tag in soup.find_all('p'):
                        text = p_tag.get_text().strip()
                        if text and len(text) > 20:  # Filter out short paragraphs
                            paragraphs.append(text)
                    
                    # Extract links
                    links = []
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag.get('href', '').strip()
                        link_text = a_tag.get_text().strip()
                        if href and link_text:
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                from urllib.parse import urljoin
                                href = urljoin(request.url, href)
                            elif not href.startswith(('http://', 'https://')):
                                continue
                            links.append({"url": href, "text": link_text})
                    
                    # Extract images
                    images = []
                    for img_tag in soup.find_all('img', src=True):
                        src = img_tag.get('src', '').strip()
                        alt = img_tag.get('alt', '').strip()
                        if src:
                            # Convert relative URLs to absolute
                            if src.startswith('/'):
                                from urllib.parse import urljoin
                                src = urljoin(request.url, src)
                            images.append({"src": src, "alt": alt})
                    
                    # Extract comprehensive metadata
                    meta_data = {}
                    
                    # Standard meta tags
                    for meta in soup.find_all('meta'):
                        name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                        content = meta.get('content')
                        if name and content:
                            meta_data[name.lower()] = content.strip()
                    
                    # Open Graph metadata
                    og_data = {}
                    for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
                        prop = meta.get('property', '')[3:]  # Remove 'og:' prefix
                        content = meta.get('content', '')
                        if prop and content:
                            og_data[prop] = content.strip()
                    if og_data:
                        meta_data['open_graph'] = og_data
                    
                    # Twitter Card metadata
                    twitter_data = {}
                    for meta in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
                        name = meta.get('name', '')[8:]  # Remove 'twitter:' prefix
                        content = meta.get('content', '')
                        if name and content:
                            twitter_data[name] = content.strip()
                    if twitter_data:
                        meta_data['twitter'] = twitter_data
                    
                    # Structured data (JSON-LD)
                    structured_data = []
                    for script in soup.find_all('script', type='application/ld+json'):
                        try:
                            data = json.loads(script.string)
                            structured_data.append(data)
                        except (json.JSONDecodeError, AttributeError, TypeError):
                            continue
                    if structured_data:
                        meta_data['structured_data'] = structured_data
                    
                    # Additional metadata
                    canonical_link = soup.find('link', rel='canonical')
                    if canonical_link:
                        meta_data['canonical_url'] = canonical_link.get('href', '').strip()
                    
                    # Favicon
                    favicon = soup.find('link', rel=['icon', 'shortcut icon'])
                    if favicon:
                        favicon_url = favicon.get('href', '').strip()
                        if favicon_url and favicon_url.startswith('/'):
                            favicon_url = urljoin(request.url, favicon_url)
                        meta_data['favicon'] = favicon_url
                    
                    # Language
                    html_tag = soup.find('html')
                    if html_tag and html_tag.get('lang'):
                        meta_data['language'] = html_tag.get('lang').strip()
                    
                    # Charset
                    charset_meta = soup.find('meta', charset=True)
                    if charset_meta:
                        meta_data['charset'] = charset_meta.get('charset', '').strip()
                    elif soup.find('meta', attrs={'http-equiv': 'Content-Type'}):
                        content_type = soup.find('meta', attrs={'http-equiv': 'Content-Type'}).get('content', '')
                        if 'charset=' in content_type:
                            meta_data['charset'] = content_type.split('charset=')[1].strip()
                    
                    # Viewport
                    viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
                    if viewport_meta:
                        meta_data['viewport'] = viewport_meta.get('content', '').strip()
                    
                    real_result = {
                        "url": request.url,
                        "title": title,
                        "headings": headings[:20],  # Limit to first 20
                        "paragraphs": paragraphs[:20],  # Limit to first 20
                        "links": links[:50],  # Limit to first 50
                        "images": images[:20],  # Limit to first 20
                        "meta": meta_data,
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                    
                    # Update task with real results
                    dev_tasks[task_id]["status"] = "completed"
                    dev_tasks[task_id]["completed_at"] = datetime.utcnow()
                    dev_tasks[task_id]["result"] = real_result
                    
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "result": real_result
                    }
                    
            except Exception as e:
                # If scraping fails, return error
                error_msg = f"Scraping failed: {str(e)}"
                dev_tasks[task_id]["status"] = "failed"
                dev_tasks[task_id]["error"] = error_msg
                dev_tasks[task_id]["completed_at"] = datetime.utcnow()
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": error_msg
                }
        else:
            # Production implementation would go here
            pass
            
    except Exception as e:
        logger.error(f"Basic scraping failed: {e}")
        raise HTTPException(status_code=500, detail="Scraping failed")

# Enhanced scraping endpoint with ML analysis
@app.post("/scrape-enhanced")
async def scrape_enhanced(
    request: EnhancedScrapeRequest,
    current_user: User = Depends(get_current_user)
):
    """Enhanced scraping with ML analysis"""
    try:
        # Create task
        task_id = str(uuid.uuid4())
        task_doc = {
            "_id": task_id,
            "url": request.url,
            "status": "processing",
            "user_id": current_user.id,
            "created_at": datetime.utcnow(),
            "enhanced": True
        }
        
        if DEV_MODE:
            dev_tasks[task_id] = task_doc
            
            # Use actual enhanced scraping instead of mock data
            try:
                import urllib.request
                import urllib.error
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin, urlparse
                import re
                
                scraped_pages = []
                urls_to_scrape = [request.url]
                visited_urls = set()
                
                # Scrape main page and find additional pages (up to max_pages)
                while urls_to_scrape and len(scraped_pages) < request.max_pages:
                    current_url = urls_to_scrape.pop(0)
                    
                    if current_url in visited_urls:
                        continue
                    visited_urls.add(current_url)
                    
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    req = urllib.request.Request(current_url, headers=headers)
                    
                    with urllib.request.urlopen(req, timeout=30) as response:
                        html_content = response.read().decode('utf-8', errors='ignore')
                        
                        # Parse HTML
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Extract content using same logic as basic scraper
                        title_tag = soup.find('title')
                        title = title_tag.get_text().strip() if title_tag else "No title found"
                        
                        headings = []
                        for h_tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                            text = h_tag.get_text().strip()
                            if text and len(text) > 2:
                                headings.append(text)
                        
                        paragraphs = []
                        for p_tag in soup.find_all('p'):
                            text = p_tag.get_text().strip()
                            if text and len(text) > 20:
                                paragraphs.append(text)
                        
                        links = []
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag.get('href', '').strip()
                            link_text = a_tag.get_text().strip()
                            if href and link_text:
                                if href.startswith('/'):
                                    href = urljoin(current_url, href)
                                elif not href.startswith(('http://', 'https://')):
                                    continue
                                links.append({"url": href, "text": link_text})
                                
                                # Add internal links for deeper scraping
                                if (request.depth > 1 and len(scraped_pages) == 0 and  # Only from main page
                                    href not in visited_urls and href not in urls_to_scrape and
                                    urlparse(href).netloc == urlparse(current_url).netloc):
                                    urls_to_scrape.append(href)
                        
                        images = []
                        for img_tag in soup.find_all('img', src=True):
                            src = img_tag.get('src', '').strip()
                            alt = img_tag.get('alt', '').strip()
                            if src:
                                if src.startswith('/'):
                                    src = urljoin(current_url, src)
                                images.append({"src": src, "alt": alt})
                        
                        # Extract comprehensive metadata for enhanced scraping
                        meta_data = {}
                        
                        # Standard meta tags
                        for meta in soup.find_all('meta'):
                            name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                            content = meta.get('content')
                            if name and content:
                                meta_data[name.lower()] = content.strip()
                        
                        # Open Graph metadata
                        og_data = {}
                        for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
                            prop = meta.get('property', '')[3:]  # Remove 'og:' prefix
                            content = meta.get('content', '')
                            if prop and content:
                                og_data[prop] = content.strip()
                        if og_data:
                            meta_data['open_graph'] = og_data
                        
                        # Twitter Card metadata
                        twitter_data = {}
                        for meta in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
                            name = meta.get('name', '')[8:]  # Remove 'twitter:' prefix
                            content = meta.get('content', '')
                            if name and content:
                                twitter_data[name] = content.strip()
                        if twitter_data:
                            meta_data['twitter'] = twitter_data
                        
                        # Structured data (JSON-LD)
                        structured_data = []
                        for script in soup.find_all('script', type='application/ld+json'):
                            try:
                                data = json.loads(script.string)
                                structured_data.append(data)
                            except (json.JSONDecodeError, AttributeError, TypeError):
                                continue
                        if structured_data:
                            meta_data['structured_data'] = structured_data
                        
                        # Additional metadata
                        canonical_link = soup.find('link', rel='canonical')
                        if canonical_link:
                            meta_data['canonical_url'] = canonical_link.get('href', '').strip()
                        
                        # Favicon
                        favicon = soup.find('link', rel=['icon', 'shortcut icon'])
                        if favicon:
                            favicon_url = favicon.get('href', '').strip()
                            if favicon_url and favicon_url.startswith('/'):
                                favicon_url = urljoin(current_url, favicon_url)
                            meta_data['favicon'] = favicon_url
                        
                        # Language
                        html_tag = soup.find('html')
                        if html_tag and html_tag.get('lang'):
                            meta_data['language'] = html_tag.get('lang').strip()
                        
                        # Charset
                        charset_meta = soup.find('meta', charset=True)
                        if charset_meta:
                            meta_data['charset'] = charset_meta.get('charset', '').strip()
                        elif soup.find('meta', attrs={'http-equiv': 'Content-Type'}):
                            content_type = soup.find('meta', attrs={'http-equiv': 'Content-Type'}).get('content', '')
                            if 'charset=' in content_type:
                                meta_data['charset'] = content_type.split('charset=')[1].strip()
                        
                        # Viewport
                        viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
                        if viewport_meta:
                            meta_data['viewport'] = viewport_meta.get('content', '').strip()
                        
                        # Additional SEO metadata
                        robots_meta = soup.find('meta', attrs={'name': 'robots'})
                        if robots_meta:
                            meta_data['robots'] = robots_meta.get('content', '').strip()
                        
                        # Page load time and HTTP headers metadata
                        response_headers = dict(response.info())
                        meta_data['http_headers'] = {
                            'content_type': response_headers.get('content-type', ''),
                            'server': response_headers.get('server', ''),
                            'last_modified': response_headers.get('last-modified', ''),
                            'cache_control': response_headers.get('cache-control', ''),
                            'etag': response_headers.get('etag', ''),
                            'content_encoding': response_headers.get('content-encoding', '')
                        }
                        
                        page_data = {
                            "url": current_url,
                            "title": title,
                            "headings": headings[:15],
                            "paragraphs": paragraphs[:15],
                            "links": links[:30],
                            "images": images[:15],
                            "meta": meta_data,
                            "content_length": len(html_content),
                            "headings_count": len(headings),
                            "paragraphs_count": len(paragraphs),
                            "links_count": len(links),
                            "images_count": len(images),
                            "scraped_at": datetime.utcnow().isoformat()
                        }
                        
                        scraped_pages.append(page_data)
                
                # Perform ML analysis if requested
                ml_analysis = None
                if request.include_ml_analysis:
                    try:
                        ml_analysis = ml_service.analyze_multiple_pages(scraped_pages)
                    except Exception as ml_error:
                        logger.warning(f"ML analysis failed: {ml_error}")
                        ml_analysis = {"error": f"ML analysis failed: {str(ml_error)}"}
                
                # Create summary
                summary = {
                    "total_pages": len(scraped_pages),
                    "total_headings": sum(p["headings_count"] for p in scraped_pages),
                    "total_paragraphs": sum(p["paragraphs_count"] for p in scraped_pages),
                    "total_links": sum(p["links_count"] for p in scraped_pages),
                    "total_images": sum(p["images_count"] for p in scraped_pages),
                    "total_content_length": sum(p["content_length"] for p in scraped_pages)
                }
                
                # Update task with real results
                dev_tasks[task_id]["status"] = "completed"
                dev_tasks[task_id]["completed_at"] = datetime.utcnow()
                dev_tasks[task_id]["result"] = {
                    "pages": scraped_pages,
                    "ml_analysis": ml_analysis,
                    "summary": summary
                }
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": dev_tasks[task_id]["result"]
                }
                
            except Exception as e:
                # If scraping fails, return error
                error_msg = f"Enhanced scraping failed: {str(e)}"
                dev_tasks[task_id]["status"] = "failed"
                dev_tasks[task_id]["error"] = error_msg
                dev_tasks[task_id]["completed_at"] = datetime.utcnow()
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": error_msg
                }
        else:
            # Production implementation would go here
            pass
            
    except Exception as e:
        logger.error(f"Enhanced scraping failed: {e}")
        raise HTTPException(status_code=500, detail="Enhanced scraping failed")

# ML Analysis endpoint
@app.post("/analyze-content")
async def analyze_content(
    content: str,
    current_user: User = Depends(get_current_user)
):
    """Analyze content using ML"""
    try:
        analysis = ml_service.analyze_content(content)
        return {
            "analysis": analysis,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Content analysis failed")

# Test endpoint for debugging
@app.get("/test")
async def test_endpoint():
    return {"message": "API is working", "endpoints": [
        "/tasks",
        "/processing-tasks", 
        "/export-tasks",
        "/processed-data",
        "/scrape-enhanced",
        "/analyze-content",
        "/health"
    ]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 