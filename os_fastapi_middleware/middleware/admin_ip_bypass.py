import ipaddress
from typing import Optional, Callable, List, Union

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AdminIPBypassMiddleware(BaseHTTPMiddleware):
    """
    Middleware to grant full access for specific admin IPs.
    If the request IP matches one of the configured admin IPs, a flag is set
    on request.state (admin_bypass=True) so downstream middlewares can skip
    their checks. Unlike the IP whitelist middleware, this middleware never
    blocks a request; it only marks bypass status when matched.

    Place this middleware early in the stack (ideally right after request
    logging) so other middlewares can observe the flag and skip accordingly.
    """

    def __init__(
        self,
        app,
        admin_ips: Optional[Union[str, List[str]]] = None,
        exempt_paths: Optional[List[str]] = None,
        trust_proxy_headers: bool = True,
        on_match: Optional[Callable[[Request, str], None]] = None,
    ): 
        super().__init__(app)
        if isinstance(admin_ips, str):
            self.admin_ips = {admin_ips}
        else:
            self.admin_ips = set(admin_ips or [])
        self.exempt_paths = exempt_paths or []
        self.trust_proxy_headers = trust_proxy_headers
        self.on_match = on_match

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
        # Do not interfere with exempt paths (e.g., health checks)
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Always compute and set the current client IP for this request
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip

        # Reset admin_bypass on every request, then set it only if current IP matches
        is_admin = client_ip in self.admin_ips
        request.state.admin_bypass = bool(is_admin)

        if is_admin and self.on_match:
            try:
                self.on_match(request, client_ip)
            except Exception:
                # Swallow callback errors to avoid affecting request flow
                pass

        return await call_next(request)
