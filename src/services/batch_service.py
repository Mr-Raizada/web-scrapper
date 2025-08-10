from typing import List, Any, Dict, Callable, Optional
import asyncio
from collections import defaultdict, deque
import logging
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BatchItem:
    id: str
    data: Any
    created_at: datetime
    status: BatchStatus = BatchStatus.PENDING
    result: Any = None
    error: str = None

class BatchProcessor:
    def __init__(
        self,
        batch_size: int = 100,
        wait_time: float = 0.1,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Batch storage
        self.batches: Dict[str, deque] = defaultdict(deque)
        self.pending_futures: Dict[str, Dict[str, asyncio.Future]] = defaultdict(dict)
        
        # Processing state
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = True
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "average_batch_time": 0.0,
            "batches_processed": 0
        }
    
    async def add_to_batch(
        self, 
        batch_type: str, 
        item: Any, 
        timeout: float = 30.0
    ) -> Any:
        """Add item to batch and return result"""
        item_id = f"{batch_type}_{time.time()}_{id(item)}"
        batch_item = BatchItem(
            id=item_id,
            data=item,
            created_at=datetime.utcnow()
        )
        
        # Create future for this item
        future = asyncio.Future()
        self.pending_futures[batch_type][item_id] = future
        self.batches[batch_type].append(batch_item)
        
        # Start processing if batch is full
        if len(self.batches[batch_type]) >= self.batch_size:
            await self._schedule_batch_processing(batch_type)
        else:
            # Schedule processing after wait time
            asyncio.create_task(self._schedule_processing(batch_type))
        
        try:
            # Wait for result with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Batch processing timeout for item {item_id}")
            future.cancel()
            raise TimeoutError(f"Batch processing timeout after {timeout} seconds")
    
    async def _schedule_processing(self, batch_type: str):
        """Schedule batch processing after wait time"""
        await asyncio.sleep(self.wait_time)
        if self.batches[batch_type] and batch_type not in self.processing_tasks:
            await self._schedule_batch_processing(batch_type)
    
    async def _schedule_batch_processing(self, batch_type: str):
        """Schedule batch processing task"""
        if batch_type in self.processing_tasks:
            return
        
        task = asyncio.create_task(self._process_batch(batch_type))
        self.processing_tasks[batch_type] = task
    
    async def _process_batch(self, batch_type: str):
        """Process a batch of items"""
        try:
            items = list(self.batches[batch_type])
            futures = self.pending_futures[batch_type]
            
            # Clear current batch
            self.batches[batch_type].clear()
            self.pending_futures[batch_type] = {}
            
            start_time = time.time()
            
            # Process items with retry logic
            results = await self._process_items_with_retry(batch_type, items)
            
            # Set results for all futures
            for item, result in zip(items, results):
                if item.id in futures:
                    if isinstance(result, Exception):
                        futures[item.id].set_exception(result)
                    else:
                        futures[item.id].set_result(result)
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats["batches_processed"] += 1
            self.stats["total_processed"] += len(items)
            self.stats["average_batch_time"] = (
                (self.stats["average_batch_time"] * (self.stats["batches_processed"] - 1) + processing_time) /
                self.stats["batches_processed"]
            )
            
            logger.info(f"Processed batch {batch_type}: {len(items)} items in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_type}: {e}")
            # Set exception for all pending futures
            for future in self.pending_futures[batch_type].values():
                if not future.done():
                    future.set_exception(e)
        finally:
            # Remove from processing tasks
            self.processing_tasks.pop(batch_type, None)
    
    async def _process_items_with_retry(
        self, 
        batch_type: str, 
        items: List[BatchItem]
    ) -> List[Any]:
        """Process items with retry logic"""
        for attempt in range(self.max_retries):
            try:
                return await self._process_items(batch_type, items)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Final attempt failed for batch {batch_type}: {e}")
                    return [e] * len(items)
                
                logger.warning(f"Attempt {attempt + 1} failed for batch {batch_type}: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return [Exception("Max retries exceeded")] * len(items)
    
    async def _process_items(self, batch_type: str, items: List[BatchItem]) -> List[Any]:
        """Process items based on batch type"""
        if batch_type == "database_operations":
            return await self._process_database_batch(items)
        elif batch_type == "api_requests":
            return await self._process_api_batch(items)
        elif batch_type == "file_operations":
            return await self._process_file_batch(items)
        else:
            # Default processing - just return the data
            return [item.data for item in items]
    
    async def _process_database_batch(self, items: List[BatchItem]) -> List[Any]:
        """Process database operations in batch"""
        # This would integrate with your database service
        # For now, just return the data
        return [item.data for item in items]
    
    async def _process_api_batch(self, items: List[BatchItem]) -> List[Any]:
        """Process API requests in batch"""
        # This would make concurrent API requests
        # For now, just return the data
        return [item.data for item in items]
    
    async def _process_file_batch(self, items: List[BatchItem]) -> List[Any]:
        """Process file operations in batch"""
        # This would handle file operations
        # For now, just return the data
        return [item.data for item in items]
    
    async def shutdown(self):
        """Shutdown the batch processor"""
        self.is_running = False
        
        # Wait for all processing tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
        
        # Cancel all pending futures
        for futures in self.pending_futures.values():
            for future in futures.values():
                if not future.done():
                    future.cancel()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics"""
        return {
            **self.stats,
            "active_batches": len(self.batches),
            "processing_tasks": len(self.processing_tasks),
            "pending_items": sum(len(batch) for batch in self.batches.values())
        }

class ConnectionPool:
    """Connection pool for managing database connections efficiently"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = deque()
        self.active_connections = 0
        self.lock = asyncio.Lock()
    
    async def get_connection(self):
        """Get a connection from the pool"""
        async with self.lock:
            if self.connections:
                return self.connections.popleft()
            
            if self.active_connections < self.max_connections:
                self.active_connections += 1
                return await self._create_connection()
            
            # Wait for a connection to become available
            while not self.connections:
                await asyncio.sleep(0.1)
            
            return self.connections.popleft()
    
    async def return_connection(self, connection):
        """Return a connection to the pool"""
        async with self.lock:
            if len(self.connections) < self.max_connections:
                self.connections.append(connection)
            else:
                await self._close_connection(connection)
                self.active_connections -= 1
    
    async def _create_connection(self):
        """Create a new connection"""
        # This would create a database connection
        # For now, return a mock connection
        return {"id": f"conn_{self.active_connections}", "created_at": datetime.utcnow()}
    
    async def _close_connection(self, connection):
        """Close a connection"""
        # This would close the database connection
        pass

class RequestBatcher:
    """Batch HTTP requests for better performance"""
    
    def __init__(self, batch_size: int = 50, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = deque()
        self.processing = False
    
    async def add_request(self, url: str, method: str = "GET", **kwargs):
        """Add a request to the batch"""
        future = asyncio.Future()
        request_data = {
            "url": url,
            "method": method,
            "kwargs": kwargs,
            "future": future,
            "timestamp": datetime.utcnow()
        }
        
        self.pending_requests.append(request_data)
        
        # Start processing if batch is full
        if len(self.pending_requests) >= self.batch_size:
            await self._process_batch()
        elif not self.processing:
            # Schedule processing after timeout
            asyncio.create_task(self._schedule_processing())
        
        return await future
    
    async def _schedule_processing(self):
        """Schedule batch processing after timeout"""
        await asyncio.sleep(self.batch_timeout)
        if self.pending_requests and not self.processing:
            await self._process_batch()
    
    async def _process_batch(self):
        """Process a batch of requests"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            requests = list(self.pending_requests)
            self.pending_requests.clear()
            
            # Process requests concurrently
            tasks = []
            for request_data in requests:
                task = asyncio.create_task(
                    self._make_request(
                        request_data["url"],
                        request_data["method"],
                        **request_data["kwargs"]
                    )
                )
                tasks.append((request_data["future"], task))
            
            # Wait for all requests to complete
            for future, task in tasks:
                try:
                    result = await task
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
        
        finally:
            self.processing = False
    
    async def _make_request(self, url: str, method: str, **kwargs):
        """Make an individual HTTP request"""
        # This would use httpx or aiohttp to make the request
        # For now, return a mock response
        return {"url": url, "method": method, "status": 200, "data": "mock_response"}

# Global instances
batch_processor = BatchProcessor()
connection_pool = ConnectionPool()
request_batcher = RequestBatcher() 