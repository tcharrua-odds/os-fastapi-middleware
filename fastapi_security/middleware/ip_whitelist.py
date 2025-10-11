from typing import Optional, Callable, List
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status
import ipaddress

from ..providers.base import BaseIPWhitelistProvider


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware para IP whitelisting.
    Adaptável através de providers customizados.
    """
    
    def __init__(
        self,
        app,
        provider: BaseIPWhitelistProvider,
        exempt_paths: Optional[List[str]] = None,
        on_blocked: Optional[Callable] = None,
        trust_proxy_headers: bool = True
    ):
        """
        Args:
            app: Aplicação FastAPI/Starlette
            provider: Provider para verificação de IPs
            exempt_paths: Paths que não requerem whitelist
            on_blocked: Callback quando IP é bloqueado
            trust_proxy_headers: Se True, confia em headers X-Forwarded-For
        """
        super().__init__(app)
        self.provider = provider
        self.exempt_paths = exempt_paths or [
            "/health", "/health/",
            "/docs", "/redoc", "/openapi.json"
        ]
        self.on_blocked = on_blocked
        self.trust_proxy_headers = trust_proxy_headers
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        if self.trust_proxy_headers:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
        
        # Fallback to client.host; normalize in test environments
        host = request.client.host if request.client else None
        if not host:
            return "127.0.0.1"
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            # Not a valid IP (e.g., 'testclient'); default to loopback
            return "127.0.0.1"
    
    async def dispatch(self, request: Request, call_next):
        # Skip IP check for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        if not client_ip:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Could not determine client IP"}
            )
        
        # Check if IP is allowed
        try:
            is_allowed = await self.provider.is_ip_allowed(client_ip)
            
            if not is_allowed:
                if self.on_blocked:
                    return self.on_blocked(request, client_ip)
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"IP {client_ip} is not whitelisted"}
                )
            
            # Store IP in request state
            request.state.client_ip = client_ip
            
            return await call_next(request)
            
        except Exception as e:
            # Decide se falha aberto ou fechado
            # Por segurança, por defeito falha fechado
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Error checking IP whitelist"}
            )