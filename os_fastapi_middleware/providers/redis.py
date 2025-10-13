from typing import Optional, List, Dict
import redis.asyncio as redis
from .base import BaseRateLimitProvider, BaseAPIKeyProvider


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


class RedisAPIKeyProvider(BaseAPIKeyProvider):
    
    def __init__(self, redis_url: str = "redis://localhost:6379", key_prefix: str = "apikey:"):
        """
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys to store account_id -> api_key mappings
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None
    
    async def init(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except AttributeError:
                await self.redis_client.close()
    
    async def validate_key(self, api_key: str) -> bool:
        """
        Validate if api_key exists by scanning all keys with prefix.
        For better performance, consider maintaining a reverse index.
        """
        if not self.redis_client:
            await self.init()
        
        # Scan all keys with prefix to find matching api_key
        cursor = 0
        while True:
            cursor, keys = await self.redis_client.scan(cursor, match=f"{self.key_prefix}*", count=100)
            
            if keys:
                values = await self.redis_client.mget(keys)
                if api_key in values:
                    return True
            
            if cursor == 0:
                break
        
        return False
    
    async def get_key_metadata(self, api_key: str) -> Optional[Dict]:
        """
        Get metadata (account_id) for the given api_key.
        """
        if not self.redis_client:
            await self.init()
        
        # Scan to find the account_id for this api_key
        cursor = 0
        while True:
            cursor, keys = await self.redis_client.scan(cursor, match=f"{self.key_prefix}*", count=100)
            
            if keys:
                values = await self.redis_client.mget(keys)
                for key, value in zip(keys, values):
                    if value == api_key:
                        # Extract account_id from key (remove prefix)
                        account_id = key[len(self.key_prefix):]
                        return {"account_id": account_id}
            
            if cursor == 0:
                break
        
        return None
    
    async def set_key(self, account_id: str, api_key: str) -> None:
        """
        Store account_id -> api_key mapping in Redis.
        """
        if not self.redis_client:
            await self.init()
        
        await self.redis_client.set(f"{self.key_prefix}{account_id}", api_key)
    
    async def delete_key(self, account_id: str) -> None:
        """
        Delete account_id -> api_key mapping from Redis.
        """
        if not self.redis_client:
            await self.init()
        
        await self.redis_client.delete(f"{self.key_prefix}{account_id}")