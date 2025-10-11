"""Dependency para IP whitelist em rotas específicas."""

from fastapi import Request
from os_fastapi_middleware.providers.base import BaseIPWhitelistProvider
from os_fastapi_middleware.exceptions import IPNotAllowedException


class IPWhitelistDependency:
    """Dependency para verificar IP whitelist em rotas específicas."""
    
    def __init__(self, provider: BaseIPWhitelistProvider):
        self.provider = provider
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else ""
    
    async def __call__(self, request: Request):
        client_ip = self._get_client_ip(request)
        
        if not client_ip:
            raise IPNotAllowedException("unknown")
        
        is_allowed = await self.provider.is_ip_allowed(client_ip)
        
        if not is_allowed:
            raise IPNotAllowedException(client_ip)
        
        return client_ip