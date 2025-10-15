from typing import Callable, Optional
from fastapi import Request

from os_fastapi_middleware.exceptions import RateLimitExceededException
from os_fastapi_middleware.providers.base import BaseRateLimitProvider


class RateLimitDependency:

    def __init__(
            self,
            provider: BaseRateLimitProvider,
            requests_per_window: int = 10,
            window_seconds: int = 60,
            key_func: Optional[Callable[[Request], str]] = None
    ):
        self.provider = provider
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func

    def _default_key_func(self, request: Request) -> str:
        if hasattr(request.state, 'api_key'):
            return f"rate_limit:api_key:{request.state.api_key}"

        # Try common proxy headers first, then fall back to the client host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                client_ip = real_ip.strip()
            else:
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
