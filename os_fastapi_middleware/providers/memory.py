from typing import Dict, List
import time
from .base import BaseAPIKeyProvider, BaseRateLimitProvider, BaseIPWhitelistProvider


class InMemoryAPIKeyProvider(BaseAPIKeyProvider):
    """Provider simples em memória para API keys (útil para testes)."""
    
    def __init__(self, valid_keys: Dict[str, dict]):
        """
        Args:
            valid_keys: Dict com API keys e seus metadados
                       Exemplo: {"key123": {"user": "john", "tier": "premium"}}
        """
        self.valid_keys = valid_keys
    
    async def validate_key(self, api_key: str) -> bool:
        return api_key in self.valid_keys
    
    async def get_key_metadata(self, api_key: str) -> dict:
        return self.valid_keys.get(api_key)


class InMemoryRateLimitProvider(BaseRateLimitProvider):
    """Provider em memória para rate limiting (útil para testes)."""
    
    def __init__(self):
        self.storage: Dict[str, List[float]] = {}
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        current_time = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.storage:
            self.storage[key] = []
        
        # Remove expired timestamps
        self.storage[key] = [
            ts for ts in self.storage[key]
            if current_time - ts < window_seconds
        ]
        
        # Check if within limit
        if len(self.storage[key]) >= limit:
            return False
        
        # Add current timestamp
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
    """Provider em memória para IP whitelist."""
    
    def __init__(self, allowed_ips: List[str]):
        self.allowed_ips = set(allowed_ips)
    
    async def is_ip_allowed(self, ip: str) -> bool:
        return ip in self.allowed_ips
    
    async def get_allowed_ips(self) -> List[str]:
        return list(self.allowed_ips)