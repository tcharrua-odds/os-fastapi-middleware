from typing import Optional, List
import redis.asyncio as redis
from .base import BaseRateLimitProvider


class RedisRateLimitProvider(BaseRateLimitProvider):
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def init(self):
        # redis.asyncio.from_url returns an async Redis client; no await needed
        self.redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except AttributeError:
                # Fallback for older versions
                await self.redis_client.close()
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        if not self.redis_client:
            await self.init()

        current = await self.redis_client.incr(key)

        if current == 1:
            await self.redis_client.expire(key, window_seconds)
        
        return current <= limit
    
    async def get_remaining_requests(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> int:
        if not self.redis_client:
            await self.init()
        
        current = await self.redis_client.get(key)
        if not current:
            return limit
        
        return max(0, limit - int(current))