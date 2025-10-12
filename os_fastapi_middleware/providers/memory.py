from typing import Dict, List
import time
from .base import BaseAPIKeyProvider, BaseRateLimitProvider, BaseIPWhitelistProvider


class InMemoryAPIKeyProvider(BaseAPIKeyProvider):
    
    def __init__(self, valid_keys: Dict[str, dict]):
        """
        Args:
            valid_keys: Dict with valid keys and metadata.
                       Example: {"key123": {"user": "john", "tier": "premium"}}
        """
        self.valid_keys = valid_keys
    
    async def validate_key(self, api_key: str) -> bool:
        return api_key in self.valid_keys
    
    async def get_key_metadata(self, api_key: str) -> dict:
        return self.valid_keys.get(api_key)


class InMemoryRateLimitProvider(BaseRateLimitProvider):
    
    def __init__(self):
        self.storage: Dict[str, List[float]] = {}
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        current_time = time.time()

        if key not in self.storage:
            self.storage[key] = []

        self.storage[key] = [
            ts for ts in self.storage[key]
            if current_time - ts < window_seconds
        ]

        if len(self.storage[key]) >= limit:
            return False

        self.storage[key].append(current_time)
        return True
    
    async def get_remaining_requests(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> int:
        if key not in self.storage:
            return limit
        
        current_time = time.time()
        valid_requests = [
            ts for ts in self.storage[key]
            if current_time - ts < window_seconds
        ]
        
        return max(0, limit - len(valid_requests))


class InMemoryIPWhitelistProvider(BaseIPWhitelistProvider):
    
    def __init__(self, allowed_ips: List[str]):
        self.allowed_ips = set(allowed_ips)
    
    async def is_ip_allowed(self, ip: str) -> bool:
        return ip in self.allowed_ips
    
    async def get_allowed_ips(self) -> List[str]:
        return list(self.allowed_ips)