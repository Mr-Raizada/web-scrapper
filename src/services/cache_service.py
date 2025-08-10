import redis
import json
import hashlib
import pickle
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta
import asyncio
import logging
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.default_expire = 3600  # 1 hour default
        
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        if args:
            key_parts.extend([str(arg) for arg in args])
        
        # Add keyword arguments (sorted for consistency)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])
        
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache with optional expiration"""
        try:
            expire = expire or self.default_expire
            serialized_value = json.dumps(value, default=str)
            return self.redis_client.setex(key, expire, serialized_value)
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key"""
        try:
            return bool(self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Error setting cache expiration: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting cache TTL: {e}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in cache"""
        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache: {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        try:
            pipeline = self.redis_client.pipeline()
            for key in keys:
                pipeline.get(key)
            results = pipeline.execute()
            
            data = {}
            for key, result in zip(keys, results):
                if result:
                    try:
                        data[key] = json.loads(result)
                    except json.JSONDecodeError:
                        data[key] = result
            
            return data
        except Exception as e:
            logger.error(f"Error getting multiple from cache: {e}")
            return {}
    
    async def set_many(self, data: Dict[str, Any], expire: int = None) -> bool:
        """Set multiple values in cache"""
        try:
            expire = expire or self.default_expire
            pipeline = self.redis_client.pipeline()
            
            for key, value in data.items():
                serialized_value = json.dumps(value, default=str)
                pipeline.setex(key, expire, serialized_value)
            
            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error setting multiple in cache: {e}")
            return False
    
    async def clear_user_cache(self, user_id: str):
        """Clear all cache entries for a specific user"""
        pattern = f"user:{user_id}:*"
        return await self.clear_pattern(pattern)
    
    async def clear_task_cache(self, task_id: str):
        """Clear all cache entries for a specific task"""
        pattern = f"task:{task_id}:*"
        return await self.clear_pattern(pattern)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0

# Global cache service instance
cache_service = CacheService()

def cache_result(expire: int = 3600, key_prefix: str = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}:{func.__name__}"
            cache_key = cache_service._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, expire)
            logger.debug(f"Cache miss for key: {cache_key}, stored result")
            
            return result
        return wrapper
    return decorator

def cache_invalidate(pattern: str):
    """Decorator to invalidate cache after function execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache_service.clear_pattern(pattern)
            logger.debug(f"Invalidated cache pattern: {pattern}")
            return result
        return wrapper
    return decorator

class CacheManager:
    """Advanced cache management with automatic cleanup and monitoring"""
    
    def __init__(self):
        self.cache_service = cache_service
        self.monitoring_enabled = True
    
    async def warm_cache(self, warmup_functions: List[callable]):
        """Warm up cache with frequently accessed data"""
        logger.info("Starting cache warmup...")
        
        for func in warmup_functions:
            try:
                await func()
                logger.debug(f"Warmed up cache for function: {func.__name__}")
            except Exception as e:
                logger.error(f"Error warming up cache for {func.__name__}: {e}")
        
        logger.info("Cache warmup completed")
    
    async def monitor_cache_performance(self, interval_seconds: int = 300):
        """Monitor cache performance and log statistics"""
        while self.monitoring_enabled:
            try:
                stats = await self.cache_service.get_cache_stats()
                hit_rate = stats.get("hit_rate", 0)
                
                if hit_rate < 80:
                    logger.warning(f"Low cache hit rate: {hit_rate:.2f}%")
                else:
                    logger.info(f"Cache hit rate: {hit_rate:.2f}%")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error monitoring cache performance: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def cleanup_expired_keys(self):
        """Clean up expired keys (Redis handles this automatically, but we can log it)"""
        try:
            # Redis automatically removes expired keys
            # This is just for monitoring purposes
            logger.debug("Cache cleanup check completed")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health status"""
        try:
            stats = await self.cache_service.get_cache_stats()
            
            # Determine health status
            hit_rate = stats.get("hit_rate", 0)
            memory_usage = stats.get("used_memory", 0)
            
            health_status = "healthy"
            issues = []
            
            if hit_rate < 70:
                health_status = "warning"
                issues.append(f"Low cache hit rate: {hit_rate:.2f}%")
            
            if memory_usage > 100_000_000:  # 100MB
                health_status = "warning"
                issues.append(f"High memory usage: {memory_usage / 1_000_000:.2f}MB")
            
            return {
                "status": health_status,
                "hit_rate": hit_rate,
                "memory_usage_mb": memory_usage / 1_000_000,
                "issues": issues,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting cache health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Global cache manager instance
cache_manager = CacheManager() 