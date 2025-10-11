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
        Verifica se o limite de taxa foi excedido.
        
        Args:
            key: Identificador único (IP, API key, etc.)
            limit: Número máximo de requests permitidos
            window_seconds: Janela de tempo em segundos
            
        Returns:
            True se dentro do limite, False se excedido
        """
        pass
    
    @abstractmethod
    async def get_remaining_requests(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> int:
        """Retorna o número de requests restantes."""
        pass


class BaseIPWhitelistProvider(ABC):
    """Interface abstrata para IP whitelist."""
    
    @abstractmethod
    async def is_ip_allowed(self, ip: str) -> bool:
        """
        Verifica se o IP está na whitelist.
        
        Args:
            ip: Endereço IP a verificar
            
        Returns:
            True se permitido, False caso contrário
        """
        pass
    
    @abstractmethod
    async def get_allowed_ips(self) -> List[str]:
        """Retorna lista de IPs permitidos."""
        pass