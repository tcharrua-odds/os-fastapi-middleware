import ipaddress
from typing import Optional, Callable, List

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from os_fastapi_middleware.providers.base import BaseIPWhitelistProvider


class IPWhitelistMiddleware(BaseHTTPMiddleware):

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
            app: Application FastAPI/Starlette
            provider: Provider to check IP whitelist
            exempt_paths: Path list to exempt from authentication
            on_blocked: Callback when IP is blocked
            trust_proxy_headers: If True, trust X-Forwarded-For and X-Real-IP headers
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
        if self.trust_proxy_headers:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()

        host = request.client.host if request.client else None
        if not host:
            return "127.0.0.1"
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            return "127.0.0.1"

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if not client_ip:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Could not determine client IP"}
            )

        try:
            is_allowed = await self.provider.is_ip_allowed(client_ip)

            if not is_allowed:
                if self.on_blocked:
                    return self.on_blocked(request, client_ip)

                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"IP {client_ip} is not whitelisted"}
                )

            request.state.client_ip = client_ip

            return await call_next(request)

        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Error checking IP whitelist"}
            )
