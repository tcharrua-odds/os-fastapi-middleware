from typing import Optional, Callable, List
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status

from os_fastapi_middleware.providers.base import BaseRateLimitProvider


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware para rate limiting.
    Adaptável através de diferentes providers (Redis, Database, Memory).
    """
    
    def __init__(
        self,
        app,
        provider: BaseRateLimitProvider,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
        exempt_paths: Optional[List[str]] = None,
        on_limit_exceeded: Optional[Callable] = None,
        add_headers: bool = True
    ):
        """
        Args:
            app: Aplicação FastAPI/Starlette
            provider: Provider para rate limiting
            requests_per_window: Número de requests permitidos
            window_seconds: Janela de tempo em segundos
            key_func: Função para gerar chave única (default: IP ou API key)
            exempt_paths: Paths que não têm rate limit
            on_limit_exceeded: Callback quando limite é excedido
            add_headers: Se True, adiciona headers X-RateLimit-* nas respostas
        """
        super().__init__(app)
        self.provider = provider
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.exempt_paths = exempt_paths or [
            "/health", "/health/",
            "/docs", "/redoc", "/openapi.json"
        ]
        self.on_limit_exceeded = on_limit_exceeded
        self.add_headers = add_headers
    
    def _default_key_func(self, request: Request) -> str:
        """
        Função padrão para gerar chave de rate limit.
        Prioriza API key, depois IP.
        """
        # Check if API key is available (from APIKeyMiddleware)
        if hasattr(request.state, 'api_key'):
            return f"rate_limit:api_key:{request.state.api_key}"
        
        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"rate_limit:ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente considerando proxies."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Generate rate limit key
        rate_limit_key = self.key_func(request)
        
        try:
            # Check rate limit
            within_limit = await self.provider.check_rate_limit(
                key=rate_limit_key,
                limit=self.requests_per_window,
                window_seconds=self.window_seconds
            )
            
            if not within_limit:
                if self.on_limit_exceeded:
                    return self.on_limit_exceeded(request, rate_limit_key)
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Maximum {self.requests_per_window} "
                                  f"requests per {self.window_seconds} seconds.",
                        "retry_after": self.window_seconds
                    },
                    headers={"Retry-After": str(self.window_seconds)}
                )
            
            # Get response
            response = await call_next(request)
            
            # Add rate limit headers if enabled
            if self.add_headers:
                remaining = await self.provider.get_remaining_requests(
                    rate_limit_key,
                    self.requests_per_window,
                    self.window_seconds
                )
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(self.window_seconds)
            
            return response
            
        except Exception as e:
            # Fail open: allow request if provider fails
            return await call_next(request)