import ipaddress
from typing import Optional, Callable, List, Union

from fastapi import Request

from os_fastapi_middleware.exceptions import ForbiddenException


class AdminIPBypassDependency:
    """
    Dependency that marks the request for admin bypass when the client IP matches
    one of the configured admin IPs. This mirrors the AdminIPBypassMiddleware behavior
    but is usable as a route dependency.

    Behavior:
    - If client IP matches, sets request.state.admin_bypass = True and returns True.
    - If no match, returns False by default.
    - If auto_error=True and no match, raises ForbiddenException("Admin IP required").

    It never blocks matching admin requests and does not modify responses.
    """

    def __init__(
        self,
        admin_ips: Union[str, List[str]],
        trust_proxy_headers: bool = True,
        on_match: Optional[Callable[[Request, str], None]] = None,
        auto_error: bool = False,
    ):
        if isinstance(admin_ips, str):
            self.admin_ips = {admin_ips}
        else:
            self.admin_ips = set(admin_ips or [])
        self.trust_proxy_headers = trust_proxy_headers
        self.on_match = on_match
        self.auto_error = auto_error

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

    async def __call__(self, request: Request):
        client_ip = self._get_client_ip(request)

        # Propagate client_ip if not already set
        if not getattr(request.state, "client_ip", None):
            request.state.client_ip = client_ip

        if client_ip in self.admin_ips:
            request.state.admin_bypass = True
            if self.on_match:
                try:
                    self.on_match(request, client_ip)
                except Exception:
                    pass
            return True

        if self.auto_error:
            raise ForbiddenException("Admin IP required")

        return False
