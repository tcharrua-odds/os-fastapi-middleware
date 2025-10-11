"""Dependency para rate limiting em rotas específicas."""

from fastapi import Request, HTTPException, status
from ..providers.base import BaseRateLimitProvider
from ..exceptions import RateLimitExceededException


class RateLimitDependency:
    """Dependency para aplicar rate limit em rotas específicas."""
    
    def __init__(
        self,
        provider: BaseRateLimitProvider,
        requests_per_window: int = 10,
        window_seconds: int = 60,
        key_func=None
    ):
        self.provider = provider
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
    
    def _default_key_func(self, request: Request) -> str:
        """Gera chave baseada em IP ou API key."""
        if hasattr(request.state, 'api_key'):
            return f"rate_limit:api_key:{request.state.api_key}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"rate_limit:ip:{client_ip}"
    
    async def __call__(self, request: Request):
        key = self.key_func(request)
        
        within_limit = await self.provider.check_rate_limit(
            key=key,
            limit=self.requests_per_window,
            window_seconds=self.window_seconds
        )
        
        if not within_limit:
            raise RateLimitExceededException(
                detail=f"Rate limit exceeded. Max {self.requests_per_window} requests per {self.window_seconds}s",
                retry_after=self.window_seconds
            )
        
        return True