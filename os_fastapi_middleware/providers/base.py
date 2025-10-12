from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime


class BaseAPIKeyProvider(ABC):
    """Interface abstrata para validação de API keys."""
    
    @abstractmethod
    async def validate_key(self, api_key: str) -> bool:
        """
        Valida se a API key é válida.
        
        Args:
            api_key: A chave API a validar
            
        Returns:
            True se válida, False caso contrário
        """
        pass
    
    @abstractmethod
    async def get_key_metadata(self, api_key: str) -> Optional[dict]:
        """
        Retorna metadados associados à API key.
        
        Returns:
            Dict com metadados ou None se não existir
        """
        pass


class BaseRateLimitProvider(ABC):
    """Interface abstrata para rate limiting."""
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        """
        Verify if the request is within the rate limit.
        
        Args:
            key: Unique key to identify the request
            limit: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            True if within limit, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_remaining_requests(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> int:
        pass


class BaseIPWhitelistProvider(ABC):
    
    @abstractmethod
    async def is_ip_allowed(self, ip: str) -> bool:
        """
        Verify if the IP is allowed.
        
        Args:
            ip: Ip address to verify
            
        Returns:
            True if allowed, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_allowed_ips(self) -> List[str]:
        pass