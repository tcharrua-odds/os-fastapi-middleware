from typing import Optional, Dict, Any
from .base import BaseRateLimitProvider, BaseAPIKeyProvider


class RedisRateLimitProvider(BaseRateLimitProvider):
    """Rate limit provider that uses an injected async Redis-like client.

    This avoids taking a hard dependency on the redis package. Provide any client
    that implements the minimal async methods used here: incr, expire, get, and
    optionally aclose/close for cleanup.

    Compatible with wrapper clients that expose get_client() returning an
    underlying Redis client that has incr/expire.
    """

    def __init__(self, redis_client: Any):
        self.redis_client = redis_client
    
    async def close(self):
        client = getattr(self, "redis_client", None)
        if client:
            # Try graceful async close if available
            close_fn = getattr(client, "aclose", None)
            if callable(close_fn):
                await close_fn()
                return
            # Fallback for older/other clients
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                try:
                    await close_fn()
                except TypeError:
                    # non-async close
                    close_fn()
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        if not self.redis_client:
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisRateLimitProvider(redis_client=...).")

        client = self.redis_client
        # Prefer incr on the provided client if available
        incr_fn = getattr(client, "incr", None)
        expire_fn = getattr(client, "expire", None)

        # If the wrapper does not expose incr (e.g., a custom RedisClient), try its underlying client
        if not callable(incr_fn) or not callable(expire_fn):
            get_client = getattr(client, "get_client", None)
            if callable(get_client):
                inner = get_client()
                incr_fn = getattr(inner, "incr", None)
                expire_fn = getattr(inner, "expire", None)
                client = inner if callable(incr_fn) and callable(expire_fn) else client

        if not callable(incr_fn) or not callable(expire_fn):
            raise RuntimeError("Provided redis_client does not expose 'incr'/'expire' nor provide an underlying client via get_client().")

        current = await incr_fn(key)

        if current == 1:
            await expire_fn(key, window_seconds)
        
        return current <= limit
    
    async def get_remaining_requests(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> int:
        if not self.redis_client:
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisRateLimitProvider(redis_client=...).")
        
        current = await self.redis_client.get(key)
        if not current:
            return limit
        
        return max(0, limit - int(current))


class RedisAPIKeyProvider(BaseAPIKeyProvider):
    """API key provider backed by an injected async Redis-like client.

    Provide any client that implements: scan, mget, get/set/delete, and
    optionally aclose/close for cleanup.
    """
    
    def __init__(self, redis_client: Any, key_prefix: str = "apikey:"):
        """
        Args:
            redis_client: An async Redis-compatible client instance (e.g., redis.asyncio.Redis).
            key_prefix: Prefix for Redis keys to store account_id -> api_key mappings
        """
        self.redis_client = redis_client
        self.key_prefix = key_prefix
    
    async def close(self):
        client = getattr(self, "redis_client", None)
        if client:
            try:
                close_fn = getattr(client, "aclose")
                if callable(close_fn):
                    await close_fn()
                    return
            except Exception:
                pass
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                try:
                    await close_fn()
                except TypeError:
                    close_fn()
    
    async def validate_key(self, api_key: str) -> bool:
        """
        Validate if api_key exists by scanning all keys with prefix.
        For better performance, consider maintaining a reverse index.
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisAPIKeyProvider(redis_client=...).")
        
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
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisAPIKeyProvider(redis_client=...).")
        
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
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisAPIKeyProvider(redis_client=...).")
        
        await self.redis_client.set(f"{self.key_prefix}{account_id}", api_key)
    
    async def delete_key(self, account_id: str) -> None:
        """
        Delete account_id -> api_key mapping from Redis.
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured. Pass a client instance to RedisAPIKeyProvider(redis_client=...).")
        
        await self.redis_client.delete(f"{self.key_prefix}{account_id}")