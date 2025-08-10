import redis.asyncio as redis
import json
import os
from typing import Any, Optional
from datetime import timedelta

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = redis.from_url(self.redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        try:
            await self.client.setex(key, expire, json.dumps(value))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            print(f"Cache expire error: {e}")
            return False
    
    async def get_many(self, keys: list) -> dict:
        """Get multiple values from cache"""
        try:
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            print(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, data: dict, expire: int = 3600) -> bool:
        """Set multiple values in cache"""
        try:
            pipeline = self.client.pipeline()
            for key, value in data.items():
                pipeline.setex(key, expire, json.dumps(value))
            await pipeline.execute()
            return True
        except Exception as e:
            print(f"Cache set_many error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear_pattern error: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check if cache is healthy"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            print(f"Cache health check error: {e}")
            return False

# Global cache instance
cache = CacheManager()

# Cache decorator
def cached(expire: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, expire)
            
            return result
        return wrapper
    return decorator 